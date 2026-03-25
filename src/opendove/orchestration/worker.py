from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from uuid import UUID

from opendove.git.manager import GitManager
from opendove.models.task import TaskStatus
from opendove.orchestration.task_runner import TaskRunner
from opendove.state.project_store import ProjectStore
from opendove.state.store import TaskStore

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="opendove-worker")


class TaskWorker:
    """Poll for IN_PROGRESS tasks and drive each through the agent pipeline."""

    def __init__(
        self,
        task_store: TaskStore,
        task_runner: TaskRunner,
        project_store: ProjectStore,
    ) -> None:
        self._task_store = task_store
        self._task_runner = task_runner
        self._project_store = project_store
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
        repo_path = None
        worktree_path = None
        try:
            task = self._task_store.get_task(task_id_str)
            if task is None or task.status is not TaskStatus.IN_PROGRESS:
                return
            if task.project_id is None:
                return

            project = self._project_store.get_project(str(task.project_id))
            if project is None:
                logger.warning("Worker: project %s not found for task %s", task.project_id, task_id)
                return

            repo_path = project.local_path
            worktree_path = repo_path.parent / "tasks" / task_id_str

            if not repo_path.exists():
                logger.info("Worker: cloning %s -> %s", project.repo_url, repo_path)
                GitManager.clone(project.repo_url, repo_path)

            branch_name = f"feat/task-{task_id_str[:8]}"
            logger.info("Worker: creating worktree at %s (branch %s)", worktree_path, branch_name)
            GitManager.create_worktree(repo_path, worktree_path, branch_name)

            task = task.model_copy(update={"branch_name": branch_name})
            self._task_store.update_task(task)

            logger.info("Worker: starting task %s - %s", task.id, task.title)
            result = self._task_runner.run(task, task.project_id, worktree_path=str(worktree_path))
            logger.info("Worker: finished task %s status=%s", task.id, result.status.value)

            if result.status.value == "approved":
                logger.info("Worker: committing and pushing worktree %s", worktree_path)
                GitManager.commit_and_push(worktree_path, f"feat: {task.title}")
        except Exception as exc:
            logger.exception("Worker: task %s failed: %s", task_id_str, exc)
        finally:
            with self._lock:
                self._inflight_task_ids.discard(task_id_str)
            if repo_path is not None and worktree_path is not None and worktree_path.exists():
                try:
                    GitManager.remove_worktree(repo_path, worktree_path)
                except Exception as exc:
                    logger.warning("Worker: failed to remove worktree %s: %s", worktree_path, exc)
