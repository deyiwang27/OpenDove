import logging

import pytest

from opendove.config import Settings
from opendove.notifications.base import Notification, NotificationBackend
from opendove.notifications.email_backend import EmailBackend
from opendove.notifications.factory import build_notification_service
from opendove.notifications.service import NotificationService


class FakeBackend(NotificationBackend):
    def __init__(self) -> None:
        self.received: list[Notification] = []

    def send(self, notification: Notification) -> None:
        self.received.append(notification)


class FailingBackend(NotificationBackend):
    def send(self, notification: Notification) -> None:
        raise RuntimeError("backend failed")


def test_notification_service_fans_out_to_all_backends() -> None:
    notification = Notification(subject="Escalation", body="Review required.")
    backend_one = FakeBackend()
    backend_two = FakeBackend()
    service = NotificationService(backends=[backend_one, backend_two])

    service.notify(notification)

    assert backend_one.received == [notification]
    assert backend_two.received == [notification]


def test_notification_service_continues_if_one_backend_fails() -> None:
    notification = Notification(subject="Escalation", body="Review required.")
    failing_backend = FailingBackend()
    succeeding_backend = FakeBackend()
    service = NotificationService(backends=[failing_backend, succeeding_backend])

    service.notify(notification)

    assert succeeding_backend.received == [notification]


def test_email_backend_skips_when_smtp_host_empty(caplog: pytest.LogCaptureFixture) -> None:
    notification = Notification(subject="Escalation", body="Review required.")
    backend = EmailBackend(
        smtp_host="",
        smtp_port=587,
        from_addr="opendove@localhost",
        to_addr="human@example.com",
    )

    with caplog.at_level(logging.WARNING):
        backend.send(notification)

    assert "smtp_host not configured" in caplog.text


def test_build_notification_service_no_backends_when_unconfigured() -> None:
    settings = Settings(smtp_host="", _env_file=None)

    service = build_notification_service(settings)

    assert service.backends == []


def test_build_notification_service_has_email_backend_when_configured() -> None:
    settings = Settings(
        smtp_host="smtp.example.com",
        notify_email_to="x@y.com",
        _env_file=None,
    )

    service = build_notification_service(settings)

    assert len(service.backends) == 1
    assert isinstance(service.backends[0], EmailBackend)
