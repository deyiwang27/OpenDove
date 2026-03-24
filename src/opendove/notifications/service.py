import logging

from opendove.notifications.base import Notification, NotificationBackend

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, backends: list[NotificationBackend] | None = None) -> None:
        self.backends: list[NotificationBackend] = backends or []

    def notify(self, notification: Notification) -> None:
        """Fan out to all configured backends. Never raises - logs errors."""
        for backend in self.backends:
            try:
                backend.send(notification)
            except Exception as exc:
                logger.error(
                    "NotificationService: backend %s failed: %s",
                    type(backend).__name__,
                    exc,
                )

    def add_backend(self, backend: NotificationBackend) -> None:
        self.backends.append(backend)
