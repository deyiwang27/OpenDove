from enum import Enum
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    repo_url: str
    local_path: Path
    default_branch: str = "main"
    status: ProjectStatus = ProjectStatus.IDLE
    active_task_id: UUID | None = None
    task_queue: list[UUID] = Field(default_factory=list)
