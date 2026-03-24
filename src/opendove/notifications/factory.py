from opendove.config import Settings
from opendove.notifications.email_backend import EmailBackend
from opendove.notifications.service import NotificationService


def build_notification_service(settings: Settings) -> NotificationService:
    """Build a NotificationService from settings.

    Returns service with no backends if email is not configured
    (notifications silently no-op).
    """
    backends = []
    if settings.smtp_host and settings.notify_email_to:
        backends.append(
            EmailBackend(
                smtp_host=settings.smtp_host,
                smtp_port=settings.smtp_port,
                from_addr=settings.notify_email_from,
                to_addr=settings.notify_email_to,
                password=settings.smtp_password,
            )
        )
    return NotificationService(backends=backends)
