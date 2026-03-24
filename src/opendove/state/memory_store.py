from opendove.models.task import Task
from opendove.state.store import TaskStore


class InMemoryTaskStore(TaskStore):
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create_task(self, task: Task) -> Task:
        stored_task = task.model_copy(deep=True)
        self._tasks[str(stored_task.id)] = stored_task
        return stored_task.model_copy(deep=True)

    def update_task(self, task: Task) -> Task:
        task_id = str(task.id)
        if task_id not in self._tasks:
            raise KeyError(task_id)

        stored_task = task.model_copy(deep=True)
        self._tasks[task_id] = stored_task
        return stored_task.model_copy(deep=True)

    def get_task(self, task_id: str) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None

        return task.model_copy(deep=True)

    def list_tasks(self) -> list[Task]:
        return [task.model_copy(deep=True) for task in self._tasks.values()]
