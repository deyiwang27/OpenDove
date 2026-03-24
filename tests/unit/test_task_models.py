from opendove.models.task import Role, Task, TaskStatus


def test_task_defaults_to_pending_status() -> None:
    task = Task(
        title="Bootstrap repository",
        intent="Create the initial OpenDove project scaffold.",
        success_criteria=["The project has a runnable package layout."],
        owner=Role.PROJECT_MANAGER,
    )

    assert task.status is TaskStatus.PENDING

