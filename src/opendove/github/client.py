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
