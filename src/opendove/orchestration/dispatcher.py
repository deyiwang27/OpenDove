from uuid import UUID

from opendove.models.project import Project, ProjectStatus
from opendove.models.task import Task, TaskStatus
from opendove.state.project_store import ProjectStore
from opendove.state.store import TaskStore


class ProjectDispatcher:
    """Enforces one-active-task-per-project with FIFO queueing."""

    def __init__(self, project_store: ProjectStore, task_store: TaskStore) -> None:
        self.project_store = project_store
        self.task_store = task_store

    def register_project(self, project: Project) -> Project:
        return self.project_store.create_project(project)

    def submit_task(self, project_id: UUID, task: Task) -> Task:
        """Enqueue task and start it immediately when the project is idle."""
        project = self.project_store.get_project(str(project_id))
        if project is None:
            raise KeyError(f"Project {project_id} not found")

        task = task.model_copy(update={"project_id": project_id})
        created_task = self.task_store.create_task(task)

        if project.status == ProjectStatus.IDLE:
            project = project.model_copy(
                update={
                    "status": ProjectStatus.ACTIVE,
                    "active_task_id": created_task.id,
                }
            )
            self.project_store.update_project(project)
            active_task = created_task.model_copy(update={"status": TaskStatus.IN_PROGRESS})
            return self.task_store.update_task(active_task)

        updated_queue = [*project.task_queue, created_task.id]
        project = project.model_copy(update={"task_queue": updated_queue})
        self.project_store.update_project(project)
        return created_task

    def on_task_complete(self, project_id: UUID, task_id: UUID) -> Task | None:
        """Promote the next queued task or return the project to idle."""
        project = self.project_store.get_project(str(project_id))
        if project is None:
            raise KeyError(f"Project {project_id} not found")

        if project.active_task_id != task_id:
            raise KeyError(f"Active task for project {project_id} does not match {task_id}")

        if not project.task_queue:
            project = project.model_copy(
                update={
                    "status": ProjectStatus.IDLE,
                    "active_task_id": None,
                }
            )
            self.project_store.update_project(project)
            return None

        next_task_id, *remaining = project.task_queue
        project = project.model_copy(
            update={
                "status": ProjectStatus.ACTIVE,
                "active_task_id": next_task_id,
                "task_queue": remaining,
            }
        )
        self.project_store.update_project(project)

        next_task = self.task_store.get_task(str(next_task_id))
        if next_task is None:
            raise KeyError(f"Queued task {next_task_id} not found in task store")

        next_task = next_task.model_copy(update={"status": TaskStatus.IN_PROGRESS})
        return self.task_store.update_task(next_task)
