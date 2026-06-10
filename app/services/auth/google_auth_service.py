"""Google OAuth2 desktop flow for Gmail API."""
import json
import threading
from app.core.logger import get_logger

log = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def authorize_from_secrets_file(client_secrets_path: str) -> str:
    """Run local-server OAuth2 flow. Returns credentials JSON string."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, scopes=SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    return _creds_to_json(creds)


def authorize_from_client_id(client_id: str, client_secret: str) -> str:
    """Build OAuth2 flow from explicit client_id/secret. Returns credentials JSON."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    return _creds_to_json(creds)


def _creds_to_json(creds) -> str:
    return json.dumps({
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    })


def get_gmail_address(credentials_json: str) -> str:
    """Fetch the authenticated Gmail address using the People API."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        import json

        data = json.loads(credentials_json)
        creds = Credentials(
            token=data["token"],
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data["client_id"],
            client_secret=data["client_secret"],
        )
        svc = build("gmail", "v1", credentials=creds)
        profile = svc.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception as exc:
        log.warning("Could not fetch Gmail address: %s", exc)
        return ""
