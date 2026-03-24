from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NotificationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Notification:
    subject: str
    body: str
    severity: NotificationSeverity = NotificationSeverity.INFO
    metadata: dict[str, Any] = field(default_factory=dict)


class NotificationBackend:
    """Protocol-style base. Implement send() to add a new backend."""

    def send(self, notification: Notification) -> None:
        raise NotImplementedError
