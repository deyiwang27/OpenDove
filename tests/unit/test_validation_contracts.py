from opendove.models.task import Role, Task
from opendove.validation.contracts import ValidationDecision, ValidationResult


def test_rejected_validation_requires_feedback() -> None:
    task = Task(
        title="Implement feature",
        intent="Build a small feature without drifting from the spec.",
        success_criteria=["Feature exists", "Tests exist"],
        owner=Role.DEVELOPER,
    )

    result = ValidationResult(
        task_id=task.id,
        decision=ValidationDecision.REJECT,
        rationale="Tests do not cover the main requirement.",
    )

    assert result.decision is ValidationDecision.REJECT
    assert "Tests" in result.rationale

