from opendove.models.project import Project
from opendove.state.project_store import ProjectStore


class InMemoryProjectStore(ProjectStore):
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

    def create_project(self, project: Project) -> Project:
        stored_project = project.model_copy(deep=True)
        self._projects[str(stored_project.id)] = stored_project
        return stored_project.model_copy(deep=True)

    def update_project(self, project: Project) -> Project:
        project_id = str(project.id)
        if project_id not in self._projects:
            raise KeyError(project_id)

        stored_project = project.model_copy(deep=True)
        self._projects[project_id] = stored_project
        return stored_project.model_copy(deep=True)

    def get_project(self, project_id: str) -> Project | None:
        project = self._projects.get(project_id)
        if project is None:
            return None

        return project.model_copy(deep=True)

    def list_projects(self) -> list[Project]:
        return [project.model_copy(deep=True) for project in self._projects.values()]
