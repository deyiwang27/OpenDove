from __future__ import annotations

import logging
from uuid import UUID

from opendove.github.client import GitHubClient
from opendove.models.task import Role, Task
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.state.project_store import ProjectStore

logger = logging.getLogger(__name__)


class IssueSyncer:
    """Poll GitHub issues and create tasks for newly discovered ones."""

    def __init__(
        self,
        github_client: GitHubClient,
        dispatcher: ProjectDispatcher,
        project_store: ProjectStore,
        issue_label: str = "opendove",
    ) -> None:
        self._github = github_client
        self._dispatcher = dispatcher
        self._project_store = project_store
        self._issue_label = issue_label

    def sync(self, project_id: UUID) -> list[Task]:
        """Fetch open labeled issues for a project and create tasks for new ones."""
        project = self._project_store.get_project(str(project_id))
        if project is None:
            logger.warning("IssueSyncer: project %s not found", project_id)
            return []

        issues = self._github.get_open_issues(self._issue_label)
        existing_numbers = self._get_synced_issue_numbers(project_id)

        new_tasks: list[Task] = []
        for issue in issues:
            if issue.number in existing_numbers:
                continue

            task = Task(
                title=issue.title,
                intent=issue.body or issue.title,
                success_criteria=[f"Resolve GitHub issue #{issue.number}: {issue.title}"],
                owner=Role.PROJECT_MANAGER,
                github_issue_number=issue.number,
            )
            created_task = self._dispatcher.submit_task(project_id, task)
            new_tasks.append(created_task)
            logger.info("IssueSyncer: created task for issue #%d", issue.number)

        return new_tasks

    def _get_synced_issue_numbers(self, project_id: UUID) -> set[int]:
        """Return GitHub issue numbers already synced for this project."""
        tasks = self._dispatcher.task_store.list_tasks()
        return {
            task.github_issue_number
            for task in tasks
            if task.project_id == project_id and task.github_issue_number is not None
        }
