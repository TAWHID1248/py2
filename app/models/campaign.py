from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    # draft | scheduled | running | paused | completed | failed | stopped

    template_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("templates.id"))
    account_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("accounts.id"))
    list_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("contact_lists.id"))

    from_name: Mapped[str | None] = mapped_column(String(200))
    reply_to: Mapped[str | None] = mapped_column(String(320))

    throttle_delay: Mapped[float] = mapped_column(Float, default=1.0)
    thread_count: Mapped[int] = mapped_column(Integer, default=4)
    use_spintax: Mapped[bool] = mapped_column(Boolean, default=False)
    use_synonyms: Mapped[bool] = mapped_column(Boolean, default=False)
    inject_unsubscribe: Mapped[bool] = mapped_column(Boolean, default=True)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    open_count: Mapped[int] = mapped_column(Integer, default=0)
    click_count: Mapped[int] = mapped_column(Integer, default=0)
    bounce_count: Mapped[int] = mapped_column(Integer, default=0)
    unsub_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sends: Mapped[list["CampaignSend"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class CampaignSend(Base):
    __tablename__ = "campaign_sends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id"), index=True)
    contact_id: Mapped[int] = mapped_column(Integer, ForeignKey("contacts.id"), index=True)

    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | sent | failed | bounced | opened | clicked

    message_id: Mapped[str | None] = mapped_column(String(500))
    tracking_pixel_token: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime)

    campaign: Mapped["Campaign"] = relationship(back_populates="sends")
