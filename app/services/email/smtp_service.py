"""SMTP connection pool with TLS/SSL, retry logic, and throttle delay."""
import smtplib
import time
import threading
from email.mime.multipart import MIMEMultipart
from app.core.logger import get_logger
from app.models.account import Account
from app.repositories.account_repository import AccountRepository
from app.core.database import get_session

log = get_logger(__name__)

_lock = threading.Lock()


class SMTPService:
    def __init__(self, account: Account, password: str):
        self.account = account
        self.password = password
        self._conn: smtplib.SMTP | None = None

    def _connect(self):
        acc = self.account
        if acc.smtp_use_tls:
            conn = smtplib.SMTP(acc.smtp_host, acc.smtp_port, timeout=30)
            conn.ehlo()
            conn.starttls()
        else:
            conn = smtplib.SMTP_SSL(acc.smtp_host, acc.smtp_port, timeout=30)
        conn.login(acc.smtp_username or acc.email, self.password)
        self._conn = conn
        log.info("SMTP connected: %s:%s", acc.smtp_host, acc.smtp_port)

    def _ensure_connected(self):
        if self._conn is None:
            self._connect()
            return
        try:
            self._conn.noop()
        except Exception:
            self._conn = None
            self._connect()

    def send(self, msg: MIMEMultipart, retries: int = 3) -> str:
        """Send a pre-built MIME message. Returns the Message-ID."""
        self._ensure_connected()
        to_addr = msg["To"]
        for attempt in range(1, retries + 1):
            try:
                self._conn.send_message(msg)
                log.info("Sent → %s", to_addr)
                return msg["Message-ID"]
            except smtplib.SMTPServerDisconnected:
                log.warning("Reconnecting (attempt %d)…", attempt)
                self._conn = None
                self._ensure_connected()
            except Exception as exc:
                if attempt == retries:
                    raise
                log.warning("Send failed (%s), retrying %d/%d…", exc, attempt, retries)
                time.sleep(2 ** attempt)
        raise RuntimeError(f"Failed to send to {to_addr} after {retries} attempts")

    def close(self):
        if self._conn:
            try:
                self._conn.quit()
            except Exception:
                pass
            self._conn = None


def test_smtp_connection(account: Account, password: str) -> tuple[bool, str]:
    """Return (success, message)."""
    try:
        svc = SMTPService(account, password)
        svc._connect()
        svc.close()
        return True, "Connection successful"
    except Exception as exc:
        return False, str(exc)
