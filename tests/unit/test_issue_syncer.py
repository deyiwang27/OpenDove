from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from opendove.api.app import app
from opendove.api.dependencies import get_scheduler, reset_state
from opendove.github.client import GitHubIssue
from opendove.models.project import Project
from opendove.models.task import Role, Task
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.scheduler.feedback_ingestor import FeedbackIngestor
from opendove.scheduler.issue_syncer import IssueSyncer
from opendove.state.memory_project_store import InMemoryProjectStore
from opendove.state.memory_store import InMemoryTaskStore


class GitHubStub:
    def __init__(self, issues: list[GitHubIssue]) -> None:
        self._issues = issues

    def get_open_issues(self, label: str) -> list[GitHubIssue]:
        del label
        return self._issues


def _build_project(repo_url: str = "https://github.com/example/opendove.git") -> Project:
    return Project(
        name="OpenDove",
        repo_url=repo_url,
        local_path=Path("/tmp/opendove/main"),
    )


def test_sync_creates_tasks_for_new_issues() -> None:
    project_store = InMemoryProjectStore()
    task_store = InMemoryTaskStore()
    dispatcher = ProjectDispatcher(project_store, task_store)
    project = dispatcher.register_project(_build_project())

    github_client = GitHubStub(
        [
        GitHubIssue(
            number=41,
            title="Implement scheduler",
            body="Add APScheduler integration.",
            labels=["opendove"],
            state="open",
            html_url="https://github.com/example/opendove/issues/41",
        ),
        GitHubIssue(
            number=42,
            title="Add sync endpoint",
            body="Expose manual project sync.",
            labels=["opendove"],
            state="open",
            html_url="https://github.com/example/opendove/issues/42",
        ),
        ]
    )
    syncer = IssueSyncer(github_client, dispatcher, project_store)

    created_tasks = syncer.sync(project.id)

    assert len(created_tasks) == 2
    assert {task.github_issue_number for task in created_tasks} == {41, 42}
    assert created_tasks[0].project_id == project.id


def test_sync_skips_already_synced_issues() -> None:
    project_store = InMemoryProjectStore()
    task_store = InMemoryTaskStore()
    dispatcher = ProjectDispatcher(project_store, task_store)
    project = dispatcher.register_project(_build_project())
    dispatcher.submit_task(
        project.id,
        Task(
            title="Existing task",
            intent="Already tracked from GitHub.",
            success_criteria=["Existing task remains the only synced issue task."],
            owner=Role.PROJECT_MANAGER,
            github_issue_number=42,
        ),
    )

    github_client = GitHubStub(
        [
        GitHubIssue(
            number=42,
            title="Existing issue",
            body="Already synced.",
            labels=["opendove"],
            state="open",
            html_url="https://github.com/example/opendove/issues/42",
        )
        ]
    )
    syncer = IssueSyncer(github_client, dispatcher, project_store)

    created_tasks = syncer.sync(project.id)

    assert created_tasks == []
    assert len(task_store.list_tasks()) == 1


def test_sync_returns_empty_when_project_not_found() -> None:
    project_store = InMemoryProjectStore()
    task_store = InMemoryTaskStore()
    dispatcher = ProjectDispatcher(project_store, task_store)

    github_client = GitHubStub([])
    syncer = IssueSyncer(github_client, dispatcher, project_store)

    assert syncer.sync(uuid4()) == []

    reset_state()
    scheduler = get_scheduler()
    with TestClient(app):
        assert scheduler.running is True
    assert scheduler.running is False


def test_feedback_ingestor_reads_markdown_files(tmp_path: Path) -> None:
    feedback_dir = tmp_path / "docs" / "feedback"
    feedback_dir.mkdir(parents=True)
    first_file = feedback_dir / "alpha.md"
    second_file = feedback_dir / "beta.md"
    first_file.write_text("# Alpha\n", encoding="utf-8")
    second_file.write_text("# Beta\n", encoding="utf-8")

    ingestor = FeedbackIngestor(tmp_path)

    items = ingestor.ingest_from_docs()

    assert len(items) == 2
    assert items[0].reference == str(first_file)
    assert items[0].content == "# Alpha\n"
    assert items[1].reference == str(second_file)
    assert items[1].content == "# Beta\n"


def test_feedback_ingestor_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    ingestor = FeedbackIngestor(tmp_path)

    assert ingestor.ingest_from_docs() == []
