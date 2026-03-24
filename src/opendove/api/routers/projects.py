from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from opendove.api.dependencies import get_dispatcher, get_project_store
from opendove.api.schemas import (
    ProjectResponse,
    RegisterProjectRequest,
    SubmitTaskRequest,
    TaskResponse,
    ValidationResultResponse,
)
from opendove.config import settings
from opendove.models.project import Project
from opendove.models.task import Task
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.state.memory_project_store import InMemoryProjectStore
from opendove.validation.contracts import ValidationResult

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_project_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        repo_url=project.repo_url,
        default_branch=project.default_branch,
        status=project.status,
        active_task_id=project.active_task_id,
        queued_task_count=len(project.task_queue),
    )


def _to_validation_result_response(
    validation_result: ValidationResult | None,
) -> ValidationResultResponse | None:
    if validation_result is None:
        return None

    return ValidationResultResponse(
        decision=validation_result.decision,
        rationale=validation_result.rationale,
    )


def _to_task_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        intent=task.intent,
        success_criteria=task.success_criteria,
        owner=task.owner,
        status=task.status,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        artifact=task.artifact,
        branch_name=task.branch_name,
        validation_result=_to_validation_result_response(task.validation_result),
    )


@router.post("", response_model=ProjectResponse, status_code=201)
def register_project(
    body: RegisterProjectRequest,
    dispatcher: ProjectDispatcher = Depends(get_dispatcher),
) -> ProjectResponse:
    """Register a new project without cloning the repo."""
    project = Project(
        name=body.name,
        repo_url=body.repo_url,
        local_path=_build_project_local_path(),
        default_branch=body.default_branch,
    )
    project = project.model_copy(update={"local_path": _build_project_local_path(project.id)})
    stored_project = dispatcher.register_project(project)
    return _to_project_response(stored_project)


def _build_project_local_path(project_id: UUID | None = None) -> Path:
    if project_id is None:
        return settings.workspace_dir / "projects"

    return settings.workspace_dir / "projects" / str(project_id) / "main"


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    project_store: InMemoryProjectStore = Depends(get_project_store),
) -> ProjectResponse:
    """Get project status and queue depth."""
    project = project_store.get_project(str(project_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return _to_project_response(project)


@router.post("/{project_id}/tasks", response_model=TaskResponse, status_code=202)
def submit_task(
    project_id: UUID,
    body: SubmitTaskRequest,
    dispatcher: ProjectDispatcher = Depends(get_dispatcher),
) -> TaskResponse:
    """Submit a task to a project and start it immediately when idle."""
    task = Task(
        title=body.title,
        intent=body.intent,
        success_criteria=body.success_criteria,
        owner=body.owner,
        max_retries=body.max_retries,
    )

    try:
        created_task = dispatcher.submit_task(project_id, task)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    return _to_task_response(created_task)
