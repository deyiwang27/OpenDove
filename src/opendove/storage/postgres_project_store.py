from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from opendove.models.project import Project, ProjectStatus
from opendove.state.project_store import ProjectStore
from opendove.storage.models import ProjectORM


def _orm_to_project(orm: ProjectORM) -> Project:
    task_queue = [UUID(task_id) for task_id in json.loads(orm.task_queue or "[]")]

    return Project(
        id=orm.id,
        name=orm.name,
        repo_url=orm.repo_url,
        local_path=Path(orm.local_path),
        default_branch=orm.default_branch,
        status=ProjectStatus(orm.status),
        active_task_id=orm.active_task_id,
        task_queue=task_queue,
    )


def _project_to_orm(project: Project) -> ProjectORM:
    return ProjectORM(
        id=project.id,
        name=project.name,
        repo_url=project.repo_url,
        local_path=str(project.local_path),
        default_branch=project.default_branch,
        status=project.status.value,
        active_task_id=project.active_task_id,
        task_queue=json.dumps([str(task_id) for task_id in project.task_queue]),
    )


class PostgresProjectStore(ProjectStore):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def create_project(self, project: Project) -> Project:
        with self._session_factory() as session:
            orm_project = _project_to_orm(project)
            session.add(orm_project)
            session.commit()
            session.refresh(orm_project)
            return _orm_to_project(orm_project)

    def update_project(self, project: Project) -> Project:
        with self._session_factory() as session:
            orm_project = session.get(ProjectORM, project.id)
            if orm_project is None:
                raise KeyError(str(project.id))

            flattened_project = _project_to_orm(project)
            orm_project.name = flattened_project.name
            orm_project.repo_url = flattened_project.repo_url
            orm_project.local_path = flattened_project.local_path
            orm_project.default_branch = flattened_project.default_branch
            orm_project.status = flattened_project.status
            orm_project.active_task_id = flattened_project.active_task_id
            orm_project.task_queue = flattened_project.task_queue

            session.commit()
            session.refresh(orm_project)
            return _orm_to_project(orm_project)

    def get_project(self, project_id: str) -> Project | None:
        try:
            parsed_project_id = UUID(project_id)
        except ValueError:
            return None

        with self._session_factory() as session:
            orm_project = session.get(ProjectORM, parsed_project_id)
            if orm_project is None:
                return None

            return _orm_to_project(orm_project)

    def list_projects(self) -> list[Project]:
        with self._session_factory() as session:
            stmt = select(ProjectORM).order_by(ProjectORM.created_at, ProjectORM.id)
            projects = session.scalars(stmt).all()
            return [_orm_to_project(project) for project in projects]
