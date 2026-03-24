from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


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
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0

