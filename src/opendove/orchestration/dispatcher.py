from uuid import UUID

from opendove.models.project import Project, ProjectStatus
from opendove.models.task import Task, TaskStatus
from opendove.state.project_store import ProjectStore
from opendove.state.store import TaskStore


class ProjectDispatcher:
    """Enforces one-active-task-per-project with dependency-aware queueing."""

    def __init__(self, project_store: ProjectStore, task_store: TaskStore) -> None:
        self.project_store = project_store
        self.task_store = task_store

    def register_project(self, project: Project) -> Project:
        return self.project_store.create_project(project)

    def submit_task(self, project_id: UUID, task: Task) -> Task:
        """Enqueue task and start it immediately when the project is idle and not paused."""
        project = self.project_store.get_project(str(project_id))
        if project is None:
            raise KeyError(f"Project {project_id} not found")

        task = task.model_copy(update={"project_id": project_id})
        self._validate_dependency_graph(task)
        created_task = self.task_store.create_task(task)

        if (
            not project.paused
            and project.status == ProjectStatus.IDLE
            and self._dependencies_are_approved(created_task)
        ):
            project = project.model_copy(
                update={
                    "status": ProjectStatus.ACTIVE,
                    "active_task_id": created_task.id,
                }
            )
            self.project_store.update_project(project)
            active_task = created_task.model_copy(update={"status": TaskStatus.QUEUED})
            return self.task_store.update_task(active_task)

        updated_queue = [*project.task_queue, created_task.id]
        project = project.model_copy(update={"task_queue": updated_queue})
        self.project_store.update_project(project)
        return created_task

    def get_next_eligible_task(self, project_id: UUID) -> Task | None:
        """Return the next queued task whose dependencies are all approved."""
        project = self.project_store.get_project(str(project_id))
        if project is None:
            raise KeyError(f"Project {project_id} not found")

        if project.paused:
            return None

        for queued_task_id in project.task_queue:
            queued_task = self.task_store.get_task(str(queued_task_id))
            if queued_task is None:
                raise KeyError(f"Queued task {queued_task_id} not found in task store")

            if self._dependencies_are_approved(queued_task):
                return queued_task

        return None

    def on_task_complete(self, project_id: UUID, task_id: UUID) -> Task | None:
        """Promote the next queued task or return the project to idle."""
        project = self.project_store.get_project(str(project_id))
        if project is None:
            raise KeyError(f"Project {project_id} not found")

        if project.active_task_id != task_id:
            raise KeyError(f"Active task for project {project_id} does not match {task_id}")

        if project.paused:
            project = project.model_copy(
                update={
                    "status": ProjectStatus.IDLE,
                    "active_task_id": None,
                }
            )
            self.project_store.update_project(project)
            return None

        next_task = self.get_next_eligible_task(project_id)
        if next_task is None:
            project = project.model_copy(
                update={
                    "status": ProjectStatus.IDLE,
                    "active_task_id": None,
                }
            )
            self.project_store.update_project(project)
            return None

        remaining = [queued_task_id for queued_task_id in project.task_queue if queued_task_id != next_task.id]
        project = project.model_copy(
            update={
                "status": ProjectStatus.ACTIVE,
                "active_task_id": next_task.id,
                "task_queue": remaining,
            }
        )
        self.project_store.update_project(project)

        next_task = next_task.model_copy(update={"status": TaskStatus.QUEUED})
        return self.task_store.update_task(next_task)

    def prioritize_queue(self, project_id: UUID, priority_map: dict[UUID, int]) -> None:
        """Re-sort project.task_queue by priority (0=P0 first, 2=P2 last, missing=P2)."""
        project = self.project_store.get_project(str(project_id))
        if project is None:
            raise KeyError(f"Project {project_id} not found")

        sorted_queue = sorted(
            project.task_queue,
            key=lambda task_id: priority_map.get(task_id, 2),
        )
        project = project.model_copy(update={"task_queue": sorted_queue})
        self.project_store.update_project(project)

    def pause_project(self, project_id: UUID) -> None:
        """Set project.paused = True."""
        project = self.project_store.get_project(str(project_id))
        if project is None:
            raise KeyError(f"Project {project_id} not found")

        project = project.model_copy(update={"paused": True})
        self.project_store.update_project(project)

    def unpause_project(self, project_id: UUID) -> Task | None:
        """Set project.paused = False. If IDLE and tasks are queued, start the next eligible one."""
        project = self.project_store.get_project(str(project_id))
        if project is None:
            raise KeyError(f"Project {project_id} not found")

        project = project.model_copy(update={"paused": False})
        self.project_store.update_project(project)

        # Re-fetch to ensure fresh state for get_next_eligible_task
        project = self.project_store.get_project(str(project_id))
        assert project is not None

        if project.status == ProjectStatus.IDLE:
            next_task = self.get_next_eligible_task(project_id)
            if next_task is not None:
                remaining = [t_id for t_id in project.task_queue if t_id != next_task.id]
                project = project.model_copy(
                    update={
                        "status": ProjectStatus.ACTIVE,
                        "active_task_id": next_task.id,
                        "task_queue": remaining,
                    }
                )
                self.project_store.update_project(project)
                next_task = next_task.model_copy(update={"status": TaskStatus.QUEUED})
                return self.task_store.update_task(next_task)

        return None

    def _dependencies_are_approved(self, task: Task) -> bool:
        for dependency_id in task.depends_on:
            dependency_task = self.task_store.get_task(str(dependency_id))
            if dependency_task is None:
                return False
            if dependency_task.status is not TaskStatus.APPROVED:
                return False

        return True

    def _validate_dependency_graph(self, task: Task) -> None:
        graph: dict[UUID, set[UUID]] = {}
        for existing_task in self.task_store.list_tasks():
            graph[existing_task.id] = set(existing_task.depends_on)

        graph[task.id] = set(task.depends_on)
        for dependency_id in task.depends_on:
            graph.setdefault(dependency_id, set())

        if self._graph_has_cycle(graph):
            raise ValueError("Circular dependency detected")

    def _graph_has_cycle(self, graph: dict[UUID, set[UUID]]) -> bool:
        visiting: set[UUID] = set()
        visited: set[UUID] = set()

        def visit(node_id: UUID) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False

            visiting.add(node_id)
            for dependency_id in graph.get(node_id, set()):
                if visit(dependency_id):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        return any(visit(node_id) for node_id in graph)
