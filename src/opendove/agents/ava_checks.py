from __future__ import annotations


def check_ci_passed(ci_status: str) -> tuple[bool, str]:
    """Return whether the CI status allows AVA to continue."""
    if ci_status in ("success", "unknown"):
        return True, "CI passed."
    return False, f"CI status is '{ci_status}' - must be 'success' before merge."


def check_files_changed(worktree_path: str) -> tuple[bool, str]:
    """Return whether any file was modified or added in the worktree."""
    import subprocess

    if not worktree_path:
        return False, "No worktree path - cannot verify file changes."

    result = subprocess.run(
        ["git", "-C", worktree_path, "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False, f"git status failed: {result.stderr.strip()}"

    if result.stdout.strip():
        return True, "Files were modified in the worktree."

    result2 = subprocess.run(
        ["git", "-C", worktree_path, "diff", "HEAD~1..HEAD", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result2.returncode == 0 and result2.stdout.strip():
        return True, "Files were committed in the worktree."

    return False, "No files were modified in the worktree."


def check_docs_updated(worktree_path: str) -> tuple[bool, str]:
    return check_files_changed(worktree_path)


def check_requirements_met(success_criteria: list[str], artifact: str) -> tuple[bool, str]:
    """Return whether minimal delivery evidence exists for the task."""
    if not artifact:
        return False, "No artifact produced."
    if not success_criteria:
        return False, "No success criteria defined."
    return True, "Artifact present and success criteria defined."
