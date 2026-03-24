from __future__ import annotations

import logging
from functools import partial
from urllib.parse import urlparse
from uuid import UUID

from opendove.agents.agent_factory import build_all_agents
from opendove.config import settings
from opendove.github.client import GitHubClient
from opendove.models.project import Project
from opendove.models.task import Task
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.orchestration.task_runner import TaskRunner
from opendove.orchestration.worker import TaskWorker
from opendove.scheduler.issue_syncer import IssueSyncer
from opendove.scheduler.scheduler import OpenDoveScheduler
from opendove.state.memory_project_store import InMemoryProjectStore
from opendove.state.memory_store import InMemoryTaskStore

logger = logging.getLogger(__name__)

_task_store = InMemoryTaskStore()
_project_store = InMemoryProjectStore()
_dispatcher = ProjectDispatcher(project_store=_project_store, task_store=_task_store)
_scheduler = OpenDoveScheduler()


def _build_worker() -> TaskWorker:
    agents = build_all_agents(settings)
    runner = TaskRunner(
        task_store=_task_store,
        dispatcher=_dispatcher,
        **agents,
    )
    return TaskWorker(task_store=_task_store, task_runner=runner)


_worker: TaskWorker | None = None


def get_task_store() -> InMemoryTaskStore:
    return _task_store


def get_project_store() -> InMemoryProjectStore:
    return _project_store


def get_dispatcher() -> ProjectDispatcher:
    return _dispatcher


def get_scheduler() -> OpenDoveScheduler:
    return _scheduler


def get_issue_syncer() -> IssueSyncer | None:
    """Returns None when github_token is not configured."""
    if not settings.github_token:
        return None

    return None


def get_project_issue_syncer(project_id: UUID) -> IssueSyncer | None:
    project = _project_store.get_project(str(project_id))
    if project is None:
        return None

    return build_issue_syncer_for_project(project)


def parse_repo_full_name(repo_url: str) -> str | None:
    parsed = urlparse(repo_url)
    if parsed.scheme in {"http", "https"} and parsed.netloc == "github.com":
        path_parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(path_parts) >= 2:
            owner, repo = path_parts[0], path_parts[1]
            return f"{owner}/{repo.removesuffix('.git')}"
        return None

    if repo_url.startswith("git@github.com:"):
        path = repo_url.removeprefix("git@github.com:").strip("/")
        owner_repo = path.removesuffix(".git")
        if owner_repo.count("/") == 1:
            return owner_repo

    return None


def build_issue_syncer_for_project(
    project: Project,
    dispatcher: ProjectDispatcher | None = None,
    project_store: InMemoryProjectStore | None = None,
) -> IssueSyncer | None:
    if not settings.github_token:
        return None

    repo_full_name = parse_repo_full_name(project.repo_url)
    if repo_full_name is None:
        logger.info("Skipping issue sync setup for non-GitHub repo URL: %s", project.repo_url)
        return None

    return IssueSyncer(
        github_client=GitHubClient(settings.github_token, repo_full_name),
        dispatcher=dispatcher or _dispatcher,
        project_store=project_store or _project_store,
        issue_label=settings.github_issue_label,
    )


def sync_project_issues(project_id: UUID) -> list[Task]:
    project = _project_store.get_project(str(project_id))
    if project is None:
        logger.warning("Skipping scheduled issue sync for unknown project %s", project_id)
        return []

    issue_syncer = build_issue_syncer_for_project(project)
    if issue_syncer is None:
        return []

    return issue_syncer.sync(project_id)


def register_project_sync_job(project: Project) -> None:
    if not settings.github_token:
        return

    if parse_repo_full_name(project.repo_url) is None:
        return

    _scheduler.add_interval_job(
        func=partial(sync_project_issues, project.id),
        minutes=settings.github_sync_interval_minutes,
        job_id=f"project-sync:{project.id}",
    )


def register_worker_job() -> None:
    _scheduler.add_seconds_job(run_worker_tick, seconds=30, job_id="task-worker")


def reset_state() -> None:
    global _worker
    _task_store._tasks.clear()
    _project_store._projects.clear()
    _scheduler.clear_jobs()
    _worker = None


def get_worker() -> TaskWorker:
    global _worker
    if _worker is None:
        _worker = _build_worker()
    return _worker


def run_worker_tick() -> None:
    get_worker().tick()
