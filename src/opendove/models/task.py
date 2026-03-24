from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from opendove.validation.contracts import ValidationResult


class Role(str, Enum):
    PRODUCT_MANAGER = "product_manager"
    PROJECT_MANAGER = "project_manager"
    LEAD_ARCHITECT = "lead_architect"
    DEVELOPER = "developer"
    AVA = "ava"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_VALIDATION = "awaiting_validation"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    intent: str
    success_criteria: list[str]
    owner: Role
    project_id: UUID | None = None
    branch_name: str = ""
    worktree_path: str = ""
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    artifact: str = ""
    depends_on: list[UUID] = Field(default_factory=list)
    risk_level: Literal["low", "architectural"] = "low"
    github_issue_number: int | None = None
    parent_issue_number: int | None = None
    github_pr_url: str = ""
    validation_result: ValidationResult | None = None
    execution_log: list[str] = Field(default_factory=list)
