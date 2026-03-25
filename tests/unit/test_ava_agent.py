from unittest.mock import Mock, patch

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from opendove.agents.ava import AVAAgent
from opendove.models.task import Role, Task, TaskStatus
from opendove.notifications.base import Notification, NotificationSeverity
from opendove.notifications.service import NotificationService
from opendove.validation.contracts import ValidationDecision


def _build_task(
    *,
    risk_level: str = "low",
    github_pr_url: str = "https://github.com/example/OpenDove/pull/123",
    max_retries: int = 3,
) -> Task:
    return Task(
        title="Phase 9 validation",
        intent="Exercise the AVA validation flow.",
        success_criteria=["CI passes", "Docs updated", "Requirements met"],
        owner=Role.AVA,
        artifact="artifact",
        risk_level=risk_level,
        github_pr_url=github_pr_url,
        max_retries=max_retries,
    )


def _build_state(task: Task, **overrides: object) -> dict:
    return {
        "task": task,
        "messages": [],
        "retry_count": 0,
        "architect_retry_count": 0,
        "worktree_path": "/tmp/worktree",
        **overrides,
    }


def test_ava_approves_and_merges_low_risk() -> None:
    github_client = Mock()
    github_client.get_ci_status.return_value = "success"
    notification_service = Mock(spec=NotificationService)
    agent = AVAAgent(
        llm=FakeListChatModel(responses=["unused"]),
        github_client=github_client,
        notification_service=notification_service,
    )
    state = _build_state(_build_task())

    with patch("opendove.agents.ava.check_files_changed", return_value=(True, "Files were modified.")):
        result = agent.run(state)

    task = result["task"]
    assert task.status is TaskStatus.APPROVED
    assert task.validation_result is not None
    assert task.validation_result.decision is ValidationDecision.APPROVE
    assert task.validation_result.checks == ["ci", "files", "requirements"]
    github_client.get_ci_status.assert_called_once_with(123)
    github_client.merge_pr.assert_called_once_with(123, merge_message="Auto-merge: Phase 9 validation")
    notification_service.notify.assert_not_called()


def test_ava_rejects_when_ci_fails() -> None:
    github_client = Mock()
    github_client.get_ci_status.return_value = "failure"
    notification_service = Mock(spec=NotificationService)
    agent = AVAAgent(
        llm=FakeListChatModel(responses=["unused"]),
        github_client=github_client,
        notification_service=notification_service,
    )
    state = _build_state(_build_task())

    with patch("opendove.agents.ava.check_files_changed", return_value=(True, "Files were modified.")):
        result = agent.run(state)

    task = result["task"]
    assert task.status is TaskStatus.REJECTED
    assert task.validation_result is not None
    assert "CI status" in task.validation_result.rationale
    assert result["retry_count"] == 1
    github_client.merge_pr.assert_not_called()
    notification_service.notify.assert_not_called()


def test_ava_rejects_when_no_files_changed() -> None:
    agent = AVAAgent(llm=FakeListChatModel(responses=["unused"]))
    state = _build_state(_build_task(github_pr_url=""), worktree_path="")

    result = agent.run(state)

    task = result["task"]
    assert task.status is TaskStatus.REJECTED
    assert task.validation_result is not None
    assert "file" in task.validation_result.rationale.lower()
    assert result["retry_count"] == 1


def test_ava_escalates_architectural_and_notifies() -> None:
    github_client = Mock()
    github_client.get_ci_status.return_value = "success"
    notification_service = Mock(spec=NotificationService)
    agent = AVAAgent(
        llm=FakeListChatModel(responses=["unused"]),
        github_client=github_client,
        notification_service=notification_service,
    )
    state = _build_state(_build_task(risk_level="architectural"))

    with patch("opendove.agents.ava.check_files_changed", return_value=(True, "Files were modified.")):
        result = agent.run(state)

    task = result["task"]
    assert task.status is TaskStatus.ESCALATED
    assert task.validation_result is not None
    assert task.validation_result.decision is ValidationDecision.ESCALATE
    assert task.validation_result.checks == ["ci", "files", "requirements"]
    github_client.request_human_review.assert_called_once_with(
        123, "Architectural change requires human review before merge."
    )
    github_client.merge_pr.assert_not_called()
    notification_service.notify.assert_called_once()
    notification = notification_service.notify.call_args.args[0]
    assert isinstance(notification, Notification)
    assert notification.severity is NotificationSeverity.WARNING


def test_ava_escalates_on_retry_limit() -> None:
    github_client = Mock()
    notification_service = Mock(spec=NotificationService)
    agent = AVAAgent(
        llm=FakeListChatModel(responses=["unused"]),
        github_client=github_client,
        notification_service=notification_service,
    )
    state = _build_state(_build_task(max_retries=3), retry_count=3)

    result = agent.run(state)

    task = result["task"]
    assert task.status is TaskStatus.ESCALATED
    assert task.validation_result is not None
    assert task.validation_result.decision is ValidationDecision.ESCALATE
    assert task.validation_result.checks == []
    github_client.get_ci_status.assert_not_called()
    notification_service.notify.assert_called_once()
    notification = notification_service.notify.call_args.args[0]
    assert isinstance(notification, Notification)
    assert notification.severity is NotificationSeverity.CRITICAL


def test_ava_no_merge_when_no_github_client() -> None:
    notification_service = Mock(spec=NotificationService)
    agent = AVAAgent(
        llm=FakeListChatModel(responses=["unused"]),
        notification_service=notification_service,
    )
    state = _build_state(_build_task(github_pr_url=""))

    with patch("opendove.agents.ava.check_files_changed", return_value=(True, "Files were modified.")):
        result = agent.run(state)

    task = result["task"]
    assert task.status is TaskStatus.APPROVED
    assert task.validation_result is not None
    assert task.validation_result.decision is ValidationDecision.APPROVE
    assert task.validation_result.checks == ["ci", "files", "requirements"]
    notification_service.notify.assert_not_called()
