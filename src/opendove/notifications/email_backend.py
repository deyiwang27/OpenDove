import logging
import smtplib
from email.mime.text import MIMEText

from opendove.notifications.base import Notification, NotificationBackend

logger = logging.getLogger(__name__)


class EmailBackend(NotificationBackend):
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_addr: str,
        to_addr: str,
        password: str = "",
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_addr = from_addr
        self.to_addr = to_addr
        self.password = password

    def send(self, notification: Notification) -> None:
        if not self.smtp_host:
            logger.warning(
                "EmailBackend: smtp_host not configured, skipping notification: %s",
                notification.subject,
            )
            return

        msg = MIMEText(notification.body)
        msg["Subject"] = f"[OpenDove] {notification.subject}"
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.password:
                    server.starttls()
                    server.login(self.from_addr, self.password)
                server.sendmail(self.from_addr, [self.to_addr], msg.as_string())
        except Exception as exc:
            logger.error("EmailBackend: failed to send notification: %s", exc)
