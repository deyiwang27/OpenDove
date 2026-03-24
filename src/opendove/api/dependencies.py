from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.state.memory_project_store import InMemoryProjectStore
from opendove.state.memory_store import InMemoryTaskStore

_task_store = InMemoryTaskStore()
_project_store = InMemoryProjectStore()
_dispatcher = ProjectDispatcher(project_store=_project_store, task_store=_task_store)


def get_task_store() -> InMemoryTaskStore:
    return _task_store


def get_project_store() -> InMemoryProjectStore:
    return _project_store


def get_dispatcher() -> ProjectDispatcher:
    return _dispatcher


def reset_state() -> None:
    _task_store._tasks.clear()
    _project_store._projects.clear()
