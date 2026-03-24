from __future__ import annotations

import logging
from uuid import UUID

from opendove.agents.base import BaseAgent
from opendove.models.task import Task
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.orchestration.graph import GraphState, build_graph
from opendove.state.store import TaskStore

logger = logging.getLogger(__name__)


class TaskRunner:
    """Bridges the dispatcher to the LangGraph execution engine.

    Runs a task through the inner graph, persists the result to the task store,
    and notifies the dispatcher that the task is complete.
    """

    def __init__(
        self,
        task_store: TaskStore,
        dispatcher: ProjectDispatcher,
        product_manager_agent: BaseAgent | None = None,
        project_manager_agent: BaseAgent | None = None,
        lead_architect_agent: BaseAgent | None = None,
        architect_review_agent: BaseAgent | None = None,
        developer_agent: BaseAgent | None = None,
        ava_agent: BaseAgent | None = None,
    ) -> None:
        self._task_store = task_store
        self._dispatcher = dispatcher
        self._agent_kwargs = {
            k: v for k, v in {
                "product_manager_agent": product_manager_agent,
                "project_manager_agent": project_manager_agent,
                "lead_architect_agent": lead_architect_agent,
                "architect_review_agent": architect_review_agent,
                "developer_agent": developer_agent,
                "ava_agent": ava_agent,
            }.items() if v is not None
        }

    def run(self, task: Task, project_id: UUID, worktree_path: str = "") -> Task:
        """Execute the task through the inner graph and persist the result."""
        logger.info(
            "TaskRunner starting",
            extra={"task_id": str(task.id), "project_id": str(project_id), "title": task.title},
        )

        graph = build_graph(**self._agent_kwargs)

        initial_state: GraphState = {
            "task": task,
            "messages": [],
            "retry_count": 0,
            "architect_retry_count": 0,
            "worktree_path": worktree_path,
        }

        result_state = graph.invoke(initial_state)
        final_task: Task = result_state["task"]
        execution_log: list[str] = result_state.get("messages", [])

        # Attach execution log to the task before persisting
        final_task = final_task.model_copy(update={"execution_log": execution_log})

        logger.info(
            "TaskRunner finished",
            extra={
                "task_id": str(task.id),
                "project_id": str(project_id),
                "final_status": final_task.status.value,
                "retry_count": final_task.retry_count,
                "log_entries": len(execution_log),
            },
        )

        # Persist the final task state
        persisted = self._task_store.update_task(final_task)

        # Notify dispatcher: dequeue next task or return project to idle
        self._dispatcher.on_task_complete(project_id, task.id)

        return persisted
