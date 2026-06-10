from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    account_type: Mapped[str] = mapped_column(String(10), default="smtp")  # smtp | gmail

    smtp_host: Mapped[str | None] = mapped_column(String(255))
    smtp_port: Mapped[int | None] = mapped_column(Integer, default=587)
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    smtp_username: Mapped[str | None] = mapped_column(String(320))
    smtp_password_enc: Mapped[str | None] = mapped_column(String(500))

    oauth_token_enc: Mapped[str | None] = mapped_column(String(2000))

    daily_limit: Mapped[int] = mapped_column(Integer, default=500)
    hourly_limit: Mapped[int] = mapped_column(Integer, default=100)
    throttle_delay: Mapped[float] = mapped_column(Float, default=1.0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
