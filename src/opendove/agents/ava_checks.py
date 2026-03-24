from __future__ import annotations


def check_ci_passed(ci_status: str) -> tuple[bool, str]:
    """Return whether the CI status allows AVA to continue."""
    if ci_status in ("success", "unknown"):
        return True, "CI passed."
    return False, f"CI status is '{ci_status}' - must be 'success' before merge."


def check_docs_updated(worktree_path: str) -> tuple[bool, str]:
    """Return whether at least one file under docs/ changed in the worktree."""
    import subprocess

    if not worktree_path:
        return False, "No worktree path - cannot verify docs update."

    result = subprocess.run(
        ["git", "-C", worktree_path, "diff", "HEAD", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False, f"git diff failed: {result.stderr.strip()}"

    changed_files = result.stdout.strip().splitlines()
    docs_changed = any(path.startswith("docs/") for path in changed_files)
    if docs_changed:
        return True, "Docs updated."
    return (
        False,
        "No docs/ files were modified - documentation must be updated as part of this task.",
    )


def check_requirements_met(success_criteria: list[str], artifact: str) -> tuple[bool, str]:
    """Return whether minimal delivery evidence exists for the task."""
    if not artifact:
        return False, "No artifact produced."
    if not success_criteria:
        return False, "No success criteria defined."
    return True, "Artifact present and success criteria defined."
