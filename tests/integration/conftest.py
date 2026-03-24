from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from opendove.models.project import Project
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.state.memory_project_store import InMemoryProjectStore
from opendove.state.memory_store import InMemoryTaskStore


@pytest.fixture()
def task_store() -> InMemoryTaskStore:
    return InMemoryTaskStore()


@pytest.fixture()
def project_store() -> InMemoryProjectStore:
    return InMemoryProjectStore()


@pytest.fixture()
def dispatcher(project_store: InMemoryProjectStore, task_store: InMemoryTaskStore) -> ProjectDispatcher:
    return ProjectDispatcher(project_store, task_store)


@pytest.fixture()
def registered_project(dispatcher: ProjectDispatcher) -> Project:
    project = Project(
        name="Test Project",
        repo_url="https://github.com/test/repo.git",
        local_path=Path("/tmp/test-repo"),
    )
    return dispatcher.register_project(project)


@pytest.fixture()
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.with_structured_output.return_value = MagicMock()
    return llm
