from datetime import datetime
from sqlalchemy.orm import Session
from app.models.campaign import Campaign, CampaignSend


class CampaignRepository:
    def __init__(self, session: Session):
        self.session = session

    def all(self) -> list[Campaign]:
        return self.session.query(Campaign).order_by(Campaign.created_at.desc()).all()

    def get(self, campaign_id: int) -> Campaign | None:
        return self.session.get(Campaign, campaign_id)

    def create(self, data: dict) -> Campaign:
        c = Campaign(**data)
        self.session.add(c)
        self.session.flush()
        return c

    def update_status(self, campaign_id: int, status: str):
        c = self.get(campaign_id)
        if c:
            c.status = status
            if status == "running" and not c.started_at:
                c.started_at = datetime.utcnow()
            if status in ("completed", "failed", "stopped"):
                c.completed_at = datetime.utcnow()
            self.session.flush()

    def increment_sent(self, campaign_id: int):
        c = self.get(campaign_id)
        if c:
            c.sent_count += 1
            self.session.flush()

    def increment_stat(self, campaign_id: int, field: str):
        c = self.get(campaign_id)
        if c and hasattr(c, field):
            setattr(c, field, getattr(c, field) + 1)
            self.session.flush()

    def delete(self, campaign_id: int) -> bool:
        c = self.get(campaign_id)
        if not c:
            return False
        self.session.delete(c)
        self.session.flush()
        return True

    # --- sends ---

    def create_send(self, campaign_id: int, contact_id: int, token: str) -> CampaignSend:
        s = CampaignSend(
            campaign_id=campaign_id,
            contact_id=contact_id,
            tracking_pixel_token=token,
        )
        self.session.add(s)
        self.session.flush()
        return s

    def get_send_by_token(self, token: str) -> CampaignSend | None:
        return self.session.query(CampaignSend).filter_by(tracking_pixel_token=token).first()

    def pending_sends(self, campaign_id: int) -> list[CampaignSend]:
        return (
            self.session.query(CampaignSend)
            .filter_by(campaign_id=campaign_id, status="pending")
            .all()
        )

    def mark_send(self, send_id: int, status: str, message_id: str = "", error: str = ""):
        s = self.session.get(CampaignSend, send_id)
        if s:
            s.status = status
            if message_id:
                s.message_id = message_id
            if error:
                s.error_message = error
            if status == "sent":
                s.sent_at = datetime.utcnow()
            self.session.flush()
