from types import SimpleNamespace
from unittest.mock import patch

from opendove.agents.ava_checks import (
    check_ci_passed,
    check_files_changed,
    check_docs_updated,
    check_requirements_met,
)


def test_check_ci_passed_success() -> None:
    passed, rationale = check_ci_passed("success")

    assert passed is True
    assert rationale == "CI passed."


def test_check_ci_passed_unknown() -> None:
    passed, rationale = check_ci_passed("unknown")

    assert passed is True
    assert rationale == "CI passed."


def test_check_ci_passed_failure() -> None:
    passed, rationale = check_ci_passed("failure")

    assert passed is False
    assert "CI status is 'failure'" in rationale


def test_check_ci_passed_pending() -> None:
    passed, rationale = check_ci_passed("pending")

    assert passed is False
    assert "CI status is 'pending'" in rationale


def test_check_files_changed_no_worktree() -> None:
    with patch("subprocess.run") as mock_run:
        passed, rationale = check_files_changed("")

    assert passed is False
    assert rationale.startswith("No worktree path")
    mock_run.assert_not_called()


def test_check_files_changed_when_git_status_has_output() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = " M src/opendove/agents/ava.py\n"
        mock_run.return_value.stderr = ""

        passed, rationale = check_files_changed("/tmp/worktree")

    assert passed is True
    assert rationale == "Files were modified in the worktree."


def test_check_files_changed_when_last_commit_has_changes() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout="src/opendove/agents/ava.py\n", stderr=""),
        ]

        passed, rationale = check_files_changed("/tmp/worktree")

    assert passed is True
    assert rationale == "Files were committed in the worktree."


def test_check_docs_updated_aliases_file_check() -> None:
    with patch("opendove.agents.ava_checks.check_files_changed", return_value=(True, "Files changed.")):
        passed, rationale = check_docs_updated("/tmp/worktree")

    assert passed is True
    assert rationale == "Files changed."


def test_check_requirements_met_no_artifact() -> None:
    passed, rationale = check_requirements_met(["Tests pass"], "")

    assert passed is False
    assert rationale == "No artifact produced."


def test_check_requirements_met_no_criteria() -> None:
    passed, rationale = check_requirements_met([], "artifact")

    assert passed is False
    assert rationale == "No success criteria defined."


def test_check_requirements_met_both_present() -> None:
    passed, rationale = check_requirements_met(["Tests pass"], "artifact")

    assert passed is True
    assert rationale == "Artifact present and success criteria defined."
