from __future__ import annotations
from uuid import UUID
from opendove.models.task import Task
from opendove.orchestration.graph import build_graph, GraphState
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.state.store import TaskStore
from opendove.agents.base import BaseAgent


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

        # Persist the final task state
        persisted = self._task_store.update_task(final_task)

        # Notify dispatcher: dequeue next task or return project to idle
        self._dispatcher.on_task_complete(project_id, task.id)

        return persisted
