from __future__ import annotations

import json
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from opendove.models.task import Role, Task, TaskStatus
from opendove.state.store import TaskStore
from opendove.storage.models import TaskORM
from opendove.validation.contracts import ValidationDecision, ValidationResult


def _orm_to_task(orm: TaskORM) -> Task:
    validation_result = None
    if orm.validation_decision is not None:
        validation_result = ValidationResult(
            task_id=orm.id,
            decision=ValidationDecision(orm.validation_decision),
            rationale=orm.validation_rationale or "",
        )

    return Task(
        id=orm.id,
        title=orm.title,
        intent=orm.intent,
        success_criteria=list(json.loads(orm.success_criteria or "[]")),
        owner=Role(orm.owner),
        project_id=orm.project_id,
        branch_name=orm.branch_name,
        worktree_path=orm.worktree_path,
        status=TaskStatus(orm.status),
        retry_count=orm.retry_count,
        max_retries=orm.max_retries,
        artifact=orm.artifact,
        validation_result=validation_result,
    )


def _task_to_orm(task: Task) -> TaskORM:
    validation_decision = None
    validation_rationale = None
    if task.validation_result is not None:
        validation_decision = task.validation_result.decision.value
        validation_rationale = task.validation_result.rationale

    return TaskORM(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        intent=task.intent,
        success_criteria=json.dumps(task.success_criteria),
        owner=task.owner.value,
        status=task.status.value,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        artifact=task.artifact,
        branch_name=task.branch_name,
        worktree_path=task.worktree_path,
        validation_decision=validation_decision,
        validation_rationale=validation_rationale,
    )


class PostgresTaskStore(TaskStore):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def create_task(self, task: Task) -> Task:
        with self._session_factory() as session:
            orm_task = _task_to_orm(task)
            session.add(orm_task)
            session.commit()
            session.refresh(orm_task)
            return _orm_to_task(orm_task)

    def update_task(self, task: Task) -> Task:
        with self._session_factory() as session:
            orm_task = session.get(TaskORM, task.id)
            if orm_task is None:
                raise KeyError(str(task.id))

            flattened_task = _task_to_orm(task)
            orm_task.project_id = flattened_task.project_id
            orm_task.title = flattened_task.title
            orm_task.intent = flattened_task.intent
            orm_task.success_criteria = flattened_task.success_criteria
            orm_task.owner = flattened_task.owner
            orm_task.status = flattened_task.status
            orm_task.retry_count = flattened_task.retry_count
            orm_task.max_retries = flattened_task.max_retries
            orm_task.artifact = flattened_task.artifact
            orm_task.branch_name = flattened_task.branch_name
            orm_task.worktree_path = flattened_task.worktree_path
            orm_task.validation_decision = flattened_task.validation_decision
            orm_task.validation_rationale = flattened_task.validation_rationale

            session.commit()
            session.refresh(orm_task)
            return _orm_to_task(orm_task)

    def get_task(self, task_id: str) -> Task | None:
        try:
            parsed_task_id = UUID(task_id)
        except ValueError:
            return None

        with self._session_factory() as session:
            orm_task = session.get(TaskORM, parsed_task_id)
            if orm_task is None:
                return None

            return _orm_to_task(orm_task)

    def list_tasks(self) -> list[Task]:
        with self._session_factory() as session:
            stmt = select(TaskORM).order_by(TaskORM.created_at, TaskORM.id)
            tasks = session.scalars(stmt).all()
            return [_orm_to_task(task) for task in tasks]
