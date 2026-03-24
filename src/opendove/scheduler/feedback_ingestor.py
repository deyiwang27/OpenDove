from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from opendove.github.client import GitHubDiscussion

logger = logging.getLogger(__name__)


@dataclass
class FeedbackItem:
    source: str
    reference: str
    content: str


class FeedbackIngestor:
    """Collect feedback from docs and GitHub-provided discussion/comment content."""

    def __init__(self, workspace_root: Path) -> None:
        self._feedback_dir = workspace_root / "docs" / "feedback"

    def ingest_from_docs(self) -> list[FeedbackItem]:
        """Read all .md files under docs/feedback/ and return them as FeedbackItems."""
        if not self._feedback_dir.exists():
            return []

        items: list[FeedbackItem] = []
        for md_file in sorted(self._feedback_dir.glob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning("FeedbackIngestor: could not read %s: %s", md_file, exc)
                continue

            items.append(
                FeedbackItem(
                    source="doc",
                    reference=str(md_file),
                    content=content,
                )
            )

        return items

    def ingest_from_discussions(self, discussions: Iterable[GitHubDiscussion]) -> list[FeedbackItem]:
        return [
            FeedbackItem(
                source="discussion",
                reference=discussion.html_url,
                content=discussion.body,
            )
            for discussion in discussions
        ]

    def ingest_from_issue_comments(
        self,
        issue_number: int,
        issue_comments: Iterable[str],
        issue_url: str = "",
    ) -> list[FeedbackItem]:
        reference = issue_url or f"issue:{issue_number}"
        return [
            FeedbackItem(
                source="issue_comment",
                reference=reference,
                content=comment,
            )
            for comment in issue_comments
        ]
