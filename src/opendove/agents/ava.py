from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from opendove.agents.ava_checks import (
    check_ci_passed,
    check_docs_updated,
    check_requirements_met,
)
from opendove.agents.base import BaseAgent
from opendove.models.task import Task, TaskStatus
from opendove.notifications.base import Notification, NotificationSeverity
from opendove.notifications.service import NotificationService
from opendove.orchestration.graph import GraphState
from opendove.validation.contracts import ValidationDecision, ValidationResult


class AVAAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = (
        "You are AVA, the Alignment & Validation Agent. "
        "You are a strict, non-bypassable gatekeeper. "
        "You validate that tasks meet their success criteria, CI passes, and docs are updated."
    )

    def __init__(
        self,
        llm: BaseChatModel,
        system_prompt: str | None = None,
        tools: list[BaseTool] | None = None,
        github_client: Any | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        super().__init__(llm, system_prompt or self.DEFAULT_SYSTEM_PROMPT, tools)
        self._github = github_client
        self._notifications = notification_service or NotificationService()

    def run(self, state: GraphState) -> GraphState:
        task: Task = state["task"]
        worktree_path = state.get("worktree_path", "")
        architect_retry_count = state.get("architect_retry_count", 0)
        retry_count = state.get("retry_count", 0)

        if retry_count >= task.max_retries or architect_retry_count >= 2:
            return self._escalate(state, task, "Retry limit reached.")

        checks_performed: list[str] = []
        failures: list[str] = []

        ci_status = self._get_ci_status(task)
        ci_ok, ci_rationale = check_ci_passed(ci_status)
        checks_performed.append("ci")
        if not ci_ok:
            failures.append(ci_rationale)

        docs_ok, docs_rationale = check_docs_updated(worktree_path)
        checks_performed.append("docs")
        if not docs_ok:
            failures.append(docs_rationale)

        req_ok, req_rationale = check_requirements_met(task.success_criteria, task.artifact)
        checks_performed.append("requirements")
        if not req_ok:
            failures.append(req_rationale)

        if failures:
            return self._reject(state, task, "; ".join(failures), checks_performed)

        if task.risk_level == "architectural":
            return self._request_human_review(state, task, checks_performed)

        return self._approve(state, task, checks_performed)

    def _get_ci_status(self, task: Task) -> str:
        if self._github and task.github_pr_url:
            try:
                pr_number = int(task.github_pr_url.rstrip("/").split("/")[-1])
                return str(self._github.get_ci_status(pr_number))
            except Exception:
                pass
        return "unknown"

    def _approve(self, state: GraphState, task: Task, checks: list[str]) -> GraphState:
        task.status = TaskStatus.APPROVED
        task.validation_result = ValidationResult(
            task_id=task.id,
            decision=ValidationDecision.APPROVE,
            rationale="All checks passed.",
            checks=checks,
        )
        if self._github and task.github_pr_url:
            try:
                pr_number = int(task.github_pr_url.rstrip("/").split("/")[-1])
                self._github.merge_pr(pr_number, merge_message=f"Auto-merge: {task.title}")
            except Exception:
                pass
        return {
            **state,
            "task": task,
            "messages": [*state["messages"], "AVA: approve."],
        }

    def _reject(
        self,
        state: GraphState,
        task: Task,
        rationale: str,
        checks: list[str],
    ) -> GraphState:
        task.status = TaskStatus.REJECTED
        task.retry_count = state.get("retry_count", 0) + 1
        task.validation_result = ValidationResult(
            task_id=task.id,
            decision=ValidationDecision.REJECT,
            rationale=rationale,
            checks=checks,
        )
        return {
            **state,
            "task": task,
            "retry_count": task.retry_count,
            "messages": [*state["messages"], f"AVA: reject. {rationale}"],
        }

    def _escalate(self, state: GraphState, task: Task, rationale: str) -> GraphState:
        task.status = TaskStatus.ESCALATED
        task.validation_result = ValidationResult(
            task_id=task.id,
            decision=ValidationDecision.ESCALATE,
            rationale=rationale,
            checks=[],
        )
        self._notifications.notify(
            Notification(
                subject=f"Task escalated: {task.title}",
                body=f"Task '{task.title}' has been escalated.\n\nReason: {rationale}",
                severity=NotificationSeverity.CRITICAL,
                metadata={"task_id": str(task.id)},
            )
        )
        return {
            **state,
            "task": task,
            "messages": [*state["messages"], f"AVA: escalate. {rationale}"],
        }

    def _request_human_review(
        self,
        state: GraphState,
        task: Task,
        checks: list[str],
    ) -> GraphState:
        task.status = TaskStatus.ESCALATED
        rationale = "Architectural change requires human review before merge."
        task.validation_result = ValidationResult(
            task_id=task.id,
            decision=ValidationDecision.ESCALATE,
            rationale=rationale,
            checks=checks,
        )
        if self._github and task.github_pr_url:
            try:
                pr_number = int(task.github_pr_url.rstrip("/").split("/")[-1])
                self._github.request_human_review(pr_number, rationale)
            except Exception:
                pass
        self._notifications.notify(
            Notification(
                subject=f"Human review required: {task.title}",
                body=(
                    f"Task '{task.title}' is an architectural change.\n\n"
                    "All checks passed but human approval is required before merge."
                ),
                severity=NotificationSeverity.WARNING,
                metadata={"task_id": str(task.id), "risk_level": "architectural"},
            )
        )
        return {
            **state,
            "task": task,
            "messages": [
                *state["messages"],
                "AVA: escalate. Architectural change - human review required.",
            ],
        }
