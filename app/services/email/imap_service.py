"""IMAP bounce monitoring — Phase 2 feature stub."""
import imaplib
import email
from app.core.logger import get_logger

log = get_logger(__name__)

HARD_BOUNCE_CODES = {"550", "551", "552", "553", "554"}
SOFT_BOUNCE_CODES = {"421", "450", "451", "452"}


class IMAPService:
    def __init__(self, host: str, port: int, username: str, password: str, use_ssl: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self._conn: imaplib.IMAP4 | None = None

    def connect(self):
        if self.use_ssl:
            self._conn = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            self._conn = imaplib.IMAP4(self.host, self.port)
        self._conn.login(self.username, self.password)
        log.info("IMAP connected: %s", self.host)

    def fetch_bounces(self) -> list[dict]:
        """Return list of {email, bounce_type, code} from inbox bounce reports."""
        if not self._conn:
            self.connect()
        bounces = []
        self._conn.select("INBOX")
        _, data = self._conn.search(None, 'SUBJECT "Delivery Status Notification"')
        for num in data[0].split():
            _, msg_data = self._conn.fetch(num, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            # parse DSN body — simplified extraction
            for part in msg.walk():
                if part.get_content_type() == "message/delivery-status":
                    payload = part.get_payload(decode=True) or b""
                    text = payload.decode(errors="replace")
                    for line in text.splitlines():
                        if line.lower().startswith("final-recipient"):
                            addr = line.split(":")[-1].strip().lstrip("rfc822;").strip()
                        if line.lower().startswith("status"):
                            code = line.split(":")[1].strip()[:3]
                            btype = "hard" if code in HARD_BOUNCE_CODES else "soft"
                            bounces.append({"email": addr, "bounce_type": btype, "code": code})
        return bounces

    def close(self):
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None
