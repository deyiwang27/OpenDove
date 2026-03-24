"""Unit tests for the CLI commands."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from opendove.cli.main import app

runner = CliRunner()

_PROJECT = {
    "id": "abc-123",
    "name": "myproject",
    "status": "idle",
    "active_task_id": None,
    "queued_task_count": 0,
    "repo_url": "https://github.com/org/repo.git",
    "default_branch": "main",
}

_TASK = {
    "id": "task-456",
    "project_id": "abc-123",
    "title": "Add health endpoint",
    "intent": "Return 200 OK",
    "success_criteria": ["GET /health returns 200"],
    "status": "in_progress",
    "retry_count": 0,
    "max_retries": 3,
    "risk_level": "low",
    "owner": "developer",
    "depends_on": [],
    "artifact": "",
    "branch_name": "",
    "github_issue_number": None,
    "parent_issue_number": None,
    "github_pr_url": "",
    "validation_result": None,
}


# ---------------------------------------------------------------------------
# project add
# ---------------------------------------------------------------------------

def test_project_add_success():
    mock_client = MagicMock()
    mock_client.register_project.return_value = _PROJECT
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, ["project", "add", "myproject", "https://github.com/org/repo.git"])
    assert result.exit_code == 0
    assert "abc-123" in result.output


def test_project_add_with_branch():
    mock_client = MagicMock()
    mock_client.register_project.return_value = _PROJECT
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        runner.invoke(app, ["project", "add", "myproject", "https://github.com/org/repo.git", "--branch", "develop"])
    mock_client.register_project.assert_called_once_with("myproject", "https://github.com/org/repo.git", "develop")


def test_project_add_connection_error():
    mock_client = MagicMock()
    mock_client.register_project.side_effect = RuntimeError("Cannot connect to OpenDove server")
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, ["project", "add", "myproject", "https://github.com/org/repo.git"])
    assert result.exit_code == 1
    assert "Error:" in result.output


# ---------------------------------------------------------------------------
# project list
# ---------------------------------------------------------------------------

def test_project_list_empty():
    mock_client = MagicMock()
    mock_client.list_projects.return_value = []
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, ["project", "list"])
    assert result.exit_code == 0
    assert "No projects" in result.output


def test_project_list_with_projects():
    mock_client = MagicMock()
    mock_client.list_projects.return_value = [
        _PROJECT,
        {**_PROJECT, "id": "def-456", "name": "second-project"},
    ]
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, ["project", "list"])
    assert result.exit_code == 0
    assert "myproject" in result.output
    assert "second-project" in result.output


# ---------------------------------------------------------------------------
# project status
# ---------------------------------------------------------------------------

def test_project_status_success():
    mock_client = MagicMock()
    mock_client.get_project.return_value = _PROJECT
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, ["project", "status", "abc-123"])
    assert result.exit_code == 0
    assert "myproject" in result.output


def test_project_status_not_found():
    mock_client = MagicMock()
    mock_client.get_project.side_effect = RuntimeError("Project not found")
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, ["project", "status", "bad-id"])
    assert result.exit_code == 1
    assert "Error:" in result.output


# ---------------------------------------------------------------------------
# task submit
# ---------------------------------------------------------------------------

def test_task_submit_success():
    mock_client = MagicMock()
    mock_client.submit_task.return_value = _TASK
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, [
            "task", "submit", "abc-123",
            "--title", "Add health endpoint",
            "--intent", "Return 200 OK",
            "--criteria", "GET /health returns 200",
        ])
    assert result.exit_code == 0
    assert "task-456" in result.output


def test_task_submit_missing_title():
    result = runner.invoke(app, [
        "task", "submit", "abc-123",
        "--intent", "Return 200 OK",
        "--criteria", "GET /health returns 200",
    ])
    assert result.exit_code == 2  # Typer usage error


def test_task_submit_multiple_criteria():
    mock_client = MagicMock()
    mock_client.submit_task.return_value = _TASK
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        runner.invoke(app, [
            "task", "submit", "abc-123",
            "--title", "T", "--intent", "I",
            "--criteria", "criterion 1",
            "--criteria", "criterion 2",
        ])
    mock_client.submit_task.assert_called_once()
    _, _, _, criteria, *_ = mock_client.submit_task.call_args.args
    assert len(criteria) == 2


# ---------------------------------------------------------------------------
# task status
# ---------------------------------------------------------------------------

def test_task_status_success():
    mock_client = MagicMock()
    mock_client.get_task.return_value = _TASK
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, ["task", "status", "task-456"])
    assert result.exit_code == 0
    assert "Add health endpoint" in result.output


def test_task_status_not_found():
    mock_client = MagicMock()
    mock_client.get_task.side_effect = RuntimeError("Task not found")
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, ["task", "status", "bad-id"])
    assert result.exit_code == 1
    assert "Error:" in result.output


# ---------------------------------------------------------------------------
# task list
# ---------------------------------------------------------------------------

def test_task_list_empty():
    mock_client = MagicMock()
    mock_client.list_tasks.return_value = []
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, ["task", "list", "abc-123"])
    assert result.exit_code == 0
    assert "No tasks" in result.output


def test_task_list_with_tasks():
    mock_client = MagicMock()
    mock_client.list_tasks.return_value = [_TASK]
    with patch("opendove.cli.main.APIClient", return_value=mock_client):
        result = runner.invoke(app, ["task", "list", "abc-123"])
    assert result.exit_code == 0
    assert "Add health endpoint" in result.output
