from __future__ import annotations

import logging
from dataclasses import dataclass

from github import Github

logger = logging.getLogger(__name__)


@dataclass
class GitHubIssue:
    number: int
    title: str
    body: str
    labels: list[str]
    state: str
    html_url: str


@dataclass
class GitHubDiscussion:
    number: int
    title: str
    body: str
    html_url: str


class GitHubClient:
    def __init__(self, token: str, repo_full_name: str) -> None:
        """repo_full_name: e.g. 'owner/repo'."""
        self._gh = Github(token) if token else Github()
        self._repo = self._gh.get_repo(repo_full_name)

    def get_open_issues(self, label: str) -> list[GitHubIssue]:
        """Return open issues with the given label."""
        issues = self._repo.get_issues(state="open", labels=[label])
        return [
            GitHubIssue(
                number=issue.number,
                title=issue.title,
                body=issue.body or "",
                labels=[repo_label.name for repo_label in issue.labels],
                state=issue.state,
                html_url=issue.html_url,
            )
            for issue in issues
        ]

    def close_issue(self, number: int) -> None:
        self._repo.get_issue(number).edit(state="closed")

    def add_label(self, number: int, label: str) -> None:
        self._repo.get_issue(number).add_to_labels(label)

    def post_comment(self, number: int, body: str) -> None:
        self._repo.get_issue(number).create_comment(body)

    def get_issue_comments(self, number: int) -> list[str]:
        return [comment.body or "" for comment in self._repo.get_issue(number).get_comments()]

    def create_sub_issue(self, parent_number: int, title: str, body: str) -> GitHubIssue:
        """Create a new issue and link it to its parent via a comment."""
        new_issue = self._repo.create_issue(title=title, body=body)
        self.post_comment(parent_number, f"Sub-task: #{new_issue.number} {title}")
        return GitHubIssue(
            number=new_issue.number,
            title=new_issue.title,
            body=new_issue.body or "",
            labels=[label.name for label in new_issue.labels],
            state=new_issue.state,
            html_url=new_issue.html_url,
        )

    def get_ci_status(self, pr_number: int) -> str:
        """Return the combined CI status for a pull request."""
        pr = self._repo.get_pull(pr_number)
        commits = list(pr.get_commits())
        if not commits:
            return "unknown"

        commit = commits[-1]
        combined_status = commit.get_combined_status()
        statuses = list(combined_status.statuses)
        if not statuses:
            check_runs = list(commit.get_check_runs())
            if not check_runs:
                return "unknown"

            conclusions = {check_run.conclusion for check_run in check_runs}
            if "failure" in conclusions:
                return "failure"
            if conclusions and all(conclusion == "success" for conclusion in conclusions):
                return "success"
            return "pending"

        return combined_status.state

    def merge_pr(self, pr_number: int, merge_message: str = "") -> None:
        """Merge a pull request using squash merge."""
        pr = self._repo.get_pull(pr_number)
        pr.merge(commit_message=merge_message, merge_method="squash")

    def request_human_review(self, issue_number: int, reason: str) -> None:
        """Flag an issue for human review and explain why."""
        self.add_label(issue_number, "needs-human-review")
        self.post_comment(issue_number, f"⚠️ **Human review required**\n\n{reason}")
