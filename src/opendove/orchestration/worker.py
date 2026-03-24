from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from uuid import UUID

from opendove.models.task import TaskStatus
from opendove.orchestration.task_runner import TaskRunner
from opendove.state.store import TaskStore

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="opendove-worker")


class TaskWorker:
    """Poll for IN_PROGRESS tasks and drive each through the agent pipeline."""

    def __init__(self, task_store: TaskStore, task_runner: TaskRunner) -> None:
        self._task_store = task_store
        self._task_runner = task_runner
        self._inflight_task_ids: set[str] = set()
        self._lock = Lock()

    def tick(self) -> None:
        """Pick up all IN_PROGRESS tasks and run each in the thread pool."""
        tasks = [task for task in self._task_store.list_tasks() if task.status is TaskStatus.IN_PROGRESS]
        if not tasks:
            return

        logger.info("Worker tick: %d task(s) in progress", len(tasks))
        for task in tasks:
            project_id = task.project_id
            if project_id is None:
                logger.warning("Task %s has no project_id, skipping", task.id)
                continue

            task_id = str(task.id)
            with self._lock:
                if task_id in self._inflight_task_ids:
                    continue
                self._inflight_task_ids.add(task_id)

            _executor.submit(self._run_task, task.id)

    def _run_task(self, task_id: UUID) -> None:
        task_id_str = str(task_id)
        try:
            task = self._task_store.get_task(task_id_str)
            if task is None or task.status is not TaskStatus.IN_PROGRESS:
                return
            if task.project_id is None:
                logger.warning("Task %s has no project_id, skipping", task.id)
                return

            logger.info("Worker: starting task %s - %s", task.id, task.title)
            self._task_runner.run(task, task.project_id)
            logger.info("Worker: finished task %s", task.id)
        except Exception as exc:
            logger.exception("Worker: task %s failed: %s", task_id_str, exc)
        finally:
            with self._lock:
                self._inflight_task_ids.discard(task_id_str)
