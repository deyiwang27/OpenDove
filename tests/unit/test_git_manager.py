import subprocess
import tempfile
from pathlib import Path

from opendove.git.manager import GitManager


def _run_git(*args: str, cwd: Path | None = None, git_dir: Path | None = None) -> str:
    cmd = ["git"]
    if git_dir is not None:
        cmd.extend(["--git-dir", str(git_dir)])
    if cwd is not None:
        cmd.extend(["-C", str(cwd)])
    cmd.extend(args)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{result.stderr.strip()}")

    return result.stdout.strip()


def _configure_git_identity(repo_path: Path) -> None:
    _run_git("config", "user.name", "OpenDove Tests", cwd=repo_path)
    _run_git("config", "user.email", "tests@example.com", cwd=repo_path)


def _initialize_remote_with_main(remote_path: Path, seed_path: Path) -> None:
    _run_git("init", "--bare", "--initial-branch=main", str(remote_path))
    _run_git("clone", str(remote_path), str(seed_path))
    _configure_git_identity(seed_path)
    (seed_path / "README.md").write_text("seed\n")
    _run_git("add", "README.md", cwd=seed_path)
    _run_git("commit", "-m", "Initial commit", cwd=seed_path)
    _run_git("push", "origin", "HEAD:main", cwd=seed_path)


def test_create_and_remove_worktree() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        remote_path = tmp_path / "remote.git"
        seed_path = tmp_path / "seed"
        repo_path = tmp_path / "repo"
        worktree_path = tmp_path / "worktrees" / "task-1"

        _initialize_remote_with_main(remote_path, seed_path)
        GitManager.clone(str(remote_path), repo_path)

        created_path = GitManager.create_worktree(repo_path, worktree_path, "feat/task-1")

        assert created_path == worktree_path
        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()

        GitManager.remove_worktree(repo_path, worktree_path)

        assert not worktree_path.exists()


def test_commit_and_push_to_local_remote() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        remote_path = tmp_path / "remote.git"
        seed_path = tmp_path / "seed"
        repo_path = tmp_path / "repo"
        worktree_path = tmp_path / "worktrees" / "task-push"
        branch_name = "feat/task-push"

        _initialize_remote_with_main(remote_path, seed_path)
        GitManager.clone(str(remote_path), repo_path)
        GitManager.create_worktree(repo_path, worktree_path, branch_name)
        _configure_git_identity(worktree_path)

        file_path = worktree_path / "feature.txt"
        file_path.write_text("implemented\n")

        GitManager.commit_and_push(worktree_path, "Implement feature")

        remote_contents = _run_git(
            "show",
            f"refs/heads/{branch_name}:feature.txt",
            git_dir=remote_path,
        )

        assert remote_contents == "implemented"
