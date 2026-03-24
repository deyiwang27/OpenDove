from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from opendove.api.dependencies import get_task_store
from opendove.api.schemas import TaskResponse, ValidationResultResponse
from opendove.models.task import Task
from opendove.state.memory_store import InMemoryTaskStore
from opendove.validation.contracts import ValidationResult

router = APIRouter(prefix="/tasks", tags=["tasks"])


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
        depends_on=task.depends_on,
        risk_level=task.risk_level,
        status=task.status,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        artifact=task.artifact,
        branch_name=task.branch_name,
        github_issue_number=task.github_issue_number,
        parent_issue_number=task.parent_issue_number,
        github_pr_url=task.github_pr_url,
        validation_result=_to_validation_result_response(task.validation_result),
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    task_store: InMemoryTaskStore = Depends(get_task_store),
) -> TaskResponse:
    """Get task detail including validation result."""
    task = task_store.get_task(str(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return _to_task_response(task)
