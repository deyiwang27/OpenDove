from typing import Protocol

from opendove.models.project import Project


class ProjectStore(Protocol):
    def create_project(self, project: Project) -> Project:
        ...

    def update_project(self, project: Project) -> Project:
        ...

    def get_project(self, project_id: str) -> Project | None:
        ...

    def list_projects(self) -> list[Project]:
        ...
