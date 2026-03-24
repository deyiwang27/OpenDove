from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ValidationDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"


class ValidationResult(BaseModel):
    task_id: UUID
    decision: ValidationDecision
    rationale: str
    checks: list[str] = Field(default_factory=list)
