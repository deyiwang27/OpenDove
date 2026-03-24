from typing import Protocol

from opendove.models.task import Task


class TaskStore(Protocol):
    def create_task(self, task: Task) -> Task:
        ...

    def update_task(self, task: Task) -> Task:
        ...

    def get_task(self, task_id: str) -> Task | None:
        ...

    def list_tasks(self) -> list[Task]:
        ...
