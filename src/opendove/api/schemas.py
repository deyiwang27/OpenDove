from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from opendove.models.project import ProjectStatus
from opendove.models.task import Role, TaskStatus
from opendove.validation.contracts import ValidationDecision


class RegisterProjectRequest(BaseModel):
    name: str
    repo_url: str
    default_branch: str = "main"


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    repo_url: str
    default_branch: str
    status: ProjectStatus
    active_task_id: UUID | None
    queued_task_count: int


class SubmitTaskRequest(BaseModel):
    title: str
    intent: str
    success_criteria: list[str]
    owner: Role = Role.PROJECT_MANAGER
    max_retries: int = 3
    depends_on: list[UUID] = Field(default_factory=list)
    risk_level: Literal["low", "architectural"] = "low"
    parent_issue_number: int | None = None


class ValidationResultResponse(BaseModel):
    decision: ValidationDecision
    rationale: str


class TaskResponse(BaseModel):
    id: UUID
    project_id: UUID | None
    title: str
    intent: str
    success_criteria: list[str]
    owner: Role
    depends_on: list[UUID]
    risk_level: Literal["low", "architectural"]
    status: TaskStatus
    retry_count: int
    max_retries: int
    artifact: str
    branch_name: str
    github_issue_number: int | None
    parent_issue_number: int | None
    github_pr_url: str
    validation_result: ValidationResultResponse | None
