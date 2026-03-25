import subprocess
from pathlib import Path


class GitManager:
    """Wraps git CLI operations for repo and worktree lifecycle."""

    @staticmethod
    def clone(repo_url: str, target_path: Path, github_token: str = "") -> None:
        """Clone repo_url into target_path. Raises RuntimeError on failure."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        url = repo_url
        if github_token and url.startswith("https://"):
            url = url.replace("https://", f"https://x-access-token:{github_token}@")
        result = subprocess.run(
            ["git", "clone", url, str(target_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")

    @staticmethod
    def create_worktree(repo_path: Path, worktree_path: Path, branch: str) -> Path:
        """Add a new git worktree at worktree_path on a new branch."""
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "-C", str(repo_path), "worktree", "add", "-b", branch, str(worktree_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git worktree add failed: {result.stderr.strip()}")
        return worktree_path

    @staticmethod
    def remove_worktree(repo_path: Path, worktree_path: Path) -> None:
        """Remove the git worktree. Ignores errors if already gone."""
        subprocess.run(
            ["git", "-C", str(repo_path), "worktree", "remove", "--force", str(worktree_path)],
            capture_output=True,
            text=True,
        )

    @staticmethod
    def commit_and_push(worktree_path: Path, message: str, remote: str = "origin", github_token: str = "") -> None:
        """Stage all changes, commit, and push the current branch."""
        for cmd in [
            ["git", "-C", str(worktree_path), "add", "-A"],
            ["git", "-C", str(worktree_path), "commit", "--allow-empty", "-m", message],
        ]:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{result.stderr.strip()}")

        original_url = ""
        if github_token:
            url_result = subprocess.run(
                ["git", "-C", str(worktree_path), "remote", "get-url", remote],
                capture_output=True, text=True,
            )
            original_url = url_result.stdout.strip()
            # Strip any existing credentials before injecting the token
            import re
            clean_url = re.sub(r"https://[^@]*@", "https://", original_url)
            authed_url = clean_url.replace("https://", f"https://x-access-token:{github_token}@", 1)
            subprocess.run(
                ["git", "-C", str(worktree_path), "remote", "set-url", remote, authed_url], check=True
            )

        try:
            result = subprocess.run(
                ["git", "-C", str(worktree_path), "push", remote, "HEAD"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git push failed: {result.stderr.strip()}")
        finally:
            if github_token and original_url:
                subprocess.run(
                    ["git", "-C", str(worktree_path), "remote", "set-url", remote, original_url]
                )

    @staticmethod
    def create_pull_request(
        repo_url: str,
        branch: str,
        title: str,
        body: str = "",
        base: str = "main",
        github_token: str = "",
    ) -> str:
        """Create a GitHub PR and return the PR HTML URL."""
        import re

        import httpx

        # Parse owner/repo from https://github.com/owner/repo.git
        match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", repo_url)
        if not match:
            raise ValueError(f"Cannot parse GitHub repo from URL: {repo_url}")
        repo_path = match.group(1)

        headers = {"Accept": "application/vnd.github+json"}
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        resp = httpx.post(
            f"https://api.github.com/repos/{repo_path}/pulls",
            json={"title": title, "head": branch, "base": base, "body": body},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["html_url"]
