"""1×1 transparent GIF open-tracking pixel."""
import base64

# Minimal 1x1 transparent GIF
_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


def gif_bytes() -> bytes:
    return _GIF


def record_open(token: str, ip: str, user_agent: str):
    from app.core.database import get_session
    from app.repositories.campaign_repository import CampaignRepository
    from app.repositories.tracking_repository import TrackingRepository
    from app.core.event_bus import bus
    from datetime import datetime

    with get_session() as s:
        repo = CampaignRepository(s)
        send = repo.get_send_by_token(token)
        if send and send.status != "opened":
            send.status = "opened"
            send.opened_at = datetime.utcnow()
            repo.increment_stat(send.campaign_id, "open_count")
            TrackingRepository(s).log_event(
                send.id, "open", ip_address=ip, user_agent=user_agent
            )
    bus.tracking_event.emit("open", token)
