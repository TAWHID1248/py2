from sqlalchemy.orm import Session
from app.models.tracking import TrackingEvent


class TrackingRepository:
    def __init__(self, session: Session):
        self.session = session

    def log_event(
        self,
        campaign_send_id: int,
        event_type: str,
        ip_address: str = "",
        user_agent: str = "",
        url: str = "",
    ) -> TrackingEvent:
        ev = TrackingEvent(
            campaign_send_id=campaign_send_id,
            event_type=event_type,
            ip_address=ip_address or None,
            user_agent=user_agent or None,
            url=url or None,
        )
        self.session.add(ev)
        self.session.flush()
        return ev

    def events_for_send(self, campaign_send_id: int) -> list[TrackingEvent]:
        return (
            self.session.query(TrackingEvent)
            .filter_by(campaign_send_id=campaign_send_id)
            .order_by(TrackingEvent.occurred_at)
            .all()
        )

    def campaign_event_counts(self, campaign_id: int) -> dict:
        from sqlalchemy import func
        from app.models.campaign import CampaignSend

        rows = (
            self.session.query(TrackingEvent.event_type, func.count(TrackingEvent.id))
            .join(CampaignSend, CampaignSend.id == TrackingEvent.campaign_send_id)
            .filter(CampaignSend.campaign_id == campaign_id)
            .group_by(TrackingEvent.event_type)
            .all()
        )
        return {event_type: count for event_type, count in rows}
