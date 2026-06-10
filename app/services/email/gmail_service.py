"""Gmail API send service with automatic token refresh."""
import base64
import json
from email.mime.multipart import MIMEMultipart
from app.core.logger import get_logger

log = get_logger(__name__)


class GmailService:
    def __init__(self, credentials_json: str):
        self._creds_json = credentials_json
        self._service = None

    def _build_service(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        data = json.loads(self._creds_json)
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # persist refreshed token back
            data["token"] = creds.token
            self._creds_json = json.dumps(data)
            log.info("Gmail OAuth token refreshed")

        self._service = build("gmail", "v1", credentials=creds)

    def send(self, msg: MIMEMultipart) -> str:
        if not self._service:
            self._build_service()
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = (
            self._service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )
        log.info("Gmail sent id=%s → %s", result["id"], msg["To"])
        return result["id"]

    def refreshed_credentials_json(self) -> str:
        """Return possibly-refreshed credentials JSON for re-storage."""
        return self._creds_json
