"""Background QThread that polls IMAP for bounce reports periodically."""
from PySide6.QtCore import QThread, Signal
from app.core.logger import get_logger

log = get_logger(__name__)


class IMAPWorker(QThread):
    bounce_found = Signal(str, str)  # email, bounce_type

    def __init__(self, host: str, port: int, username: str, password: str,
                 use_ssl: bool = True, poll_interval: int = 300, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.poll_interval = poll_interval
        self._stop = False

    def run(self):
        from app.services.email.imap_service import IMAPService
        from app.core.database import get_session
        from app.repositories.contact_repository import ContactRepository

        svc = IMAPService(self.host, self.port, self.username, self.password, self.use_ssl)
        while not self._stop:
            try:
                svc.connect()
                bounces = svc.fetch_bounces()
                svc.close()
                for b in bounces:
                    email = b.get("email", "")
                    btype = b.get("bounce_type", "hard")
                    if email:
                        if btype == "hard":
                            with get_session() as s:
                                ContactRepository(s).suppress(email, reason=f"hard bounce")
                        self.bounce_found.emit(email, btype)
                        log.info("Bounce %s: %s", btype, email)
            except Exception as exc:
                log.warning("IMAP poll error: %s", exc)

            # Sleep in 5-second slices so we can stop cleanly
            for _ in range(self.poll_interval // 5):
                if self._stop:
                    break
                self.msleep(5000)

    def stop(self):
        self._stop = True
        self.quit()
