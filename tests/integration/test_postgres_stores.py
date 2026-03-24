import os
import re
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from opendove.models.project import Project, ProjectStatus
from opendove.models.task import Role, Task, TaskStatus
from opendove.storage.engine import make_engine
from opendove.storage.models import Base
from opendove.storage.postgres_project_store import PostgresProjectStore
from opendove.storage.postgres_task_store import PostgresTaskStore
from opendove.validation.contracts import ValidationDecision, ValidationResult

DATABASE_URL = os.getenv("OPENDOVE_DATABASE_URL")
REQUIRES_DATABASE = pytest.mark.skipif(
    not DATABASE_URL,
    reason="OPENDOVE_DATABASE_URL is not set",
)


@pytest.fixture
def postgres_session_factory() -> Iterator[sessionmaker[Session]]:
    if DATABASE_URL is None:
        pytest.skip("OPENDOVE_DATABASE_URL is not set")

    engine = make_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def make_task() -> Task:
    task_id = uuid4()
    return Task(
        id=task_id,
        title="Implement persistence",
        intent="Persist tasks in PostgreSQL",
        success_criteria=["task survives restart", "task can be updated"],
        owner=Role.DEVELOPER,
        project_id=uuid4(),
        branch_name="feat/postgres-store",
        worktree_path="/tmp/opendove/worktree",
        status=TaskStatus.AWAITING_VALIDATION,
        retry_count=1,
        max_retries=4,
        artifact="migration.sql",
        validation_result=ValidationResult(
            task_id=task_id,
            decision=ValidationDecision.REJECT,
            rationale="Add more persistence coverage",
        ),
    )


def make_project() -> Project:
    return Project(
        name="OpenDove",
        repo_url="https://github.com/example/opendove",
        local_path=Path("/tmp/opendove"),
        default_branch="main",
        status=ProjectStatus.ACTIVE,
        active_task_id=uuid4(),
        task_queue=[uuid4(), uuid4()],
    )


@pytest.mark.integration
@REQUIRES_DATABASE
def test_postgres_task_store_create_and_get(postgres_session_factory) -> None:
    store = PostgresTaskStore(postgres_session_factory)
    task = make_task()

    created = store.create_task(task)
    fetched = store.get_task(str(task.id))

    assert created == task
    assert fetched == task


@pytest.mark.integration
@REQUIRES_DATABASE
def test_postgres_task_store_update(postgres_session_factory) -> None:
    store = PostgresTaskStore(postgres_session_factory)
    created = store.create_task(make_task())
    updated_task = created.model_copy(
        update={
            "status": TaskStatus.APPROVED,
            "retry_count": 2,
            "artifact": "validated-artifact.md",
            "validation_result": ValidationResult(
                task_id=created.id,
                decision=ValidationDecision.APPROVE,
                rationale="Looks good",
            ),
        },
        deep=True,
    )

    updated = store.update_task(updated_task)

    assert updated == updated_task
    assert store.get_task(str(created.id)) == updated_task


@pytest.mark.integration
@REQUIRES_DATABASE
def test_postgres_task_store_update_raises_on_missing(postgres_session_factory) -> None:
    store = PostgresTaskStore(postgres_session_factory)
    task = make_task()

    with pytest.raises(KeyError, match=re.escape(str(task.id))):
        store.update_task(task)


@pytest.mark.integration
@REQUIRES_DATABASE
def test_postgres_task_store_list(postgres_session_factory) -> None:
    store = PostgresTaskStore(postgres_session_factory)
    first = store.create_task(make_task())
    second = store.create_task(make_task())

    assert store.list_tasks() == [first, second]


@pytest.mark.integration
@REQUIRES_DATABASE
def test_postgres_project_store_create_and_get(postgres_session_factory) -> None:
    store = PostgresProjectStore(postgres_session_factory)
    project = make_project()

    created = store.create_project(project)
    fetched = store.get_project(str(project.id))

    assert created == project
    assert fetched == project


@pytest.mark.integration
@REQUIRES_DATABASE
def test_postgres_project_store_update(postgres_session_factory) -> None:
    store = PostgresProjectStore(postgres_session_factory)
    created = store.create_project(make_project())
    updated_project = created.model_copy(
        update={
            "status": ProjectStatus.ARCHIVED,
            "default_branch": "develop",
            "task_queue": [uuid4()],
            "active_task_id": uuid4(),
        },
        deep=True,
    )

    updated = store.update_project(updated_project)

    assert updated == updated_project
    assert store.get_project(str(created.id)) == updated_project


@pytest.mark.integration
@REQUIRES_DATABASE
def test_postgres_project_store_update_raises_on_missing(postgres_session_factory) -> None:
    store = PostgresProjectStore(postgres_session_factory)
    project = make_project()

    with pytest.raises(KeyError, match=re.escape(str(project.id))):
        store.update_project(project)


@pytest.mark.integration
@REQUIRES_DATABASE
def test_postgres_project_store_list(postgres_session_factory) -> None:
    store = PostgresProjectStore(postgres_session_factory)
    first = store.create_project(make_project())
    second = store.create_project(make_project())

    assert store.list_projects() == [first, second]
