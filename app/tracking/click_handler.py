"""Click tracking redirect handler."""


def record_click(token: str, url: str, ip: str, user_agent: str):
    from app.core.database import get_session
    from app.repositories.campaign_repository import CampaignRepository
    from app.repositories.tracking_repository import TrackingRepository
    from app.core.event_bus import bus

    with get_session() as s:
        repo = CampaignRepository(s)
        send = repo.get_send_by_token(token)
        if send:
            repo.increment_stat(send.campaign_id, "click_count")
            TrackingRepository(s).log_event(
                send.id, "click", ip_address=ip, user_agent=user_agent, url=url
            )
    bus.tracking_event.emit("click", token)
