from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_send_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaign_sends.id"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(20))  # open | click | bounce | unsub
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    url: Mapped[str | None] = mapped_column(String(2000))  # for click events
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
