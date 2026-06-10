from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ContactList(Base):
    __tablename__ = "contact_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    members: Mapped[list["ContactListMember"]] = relationship(
        back_populates="contact_list", cascade="all, delete-orphan"
    )


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    company: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50))
    custom1: Mapped[str | None] = mapped_column(String(500))
    custom2: Mapped[str | None] = mapped_column(String(500))
    custom3: Mapped[str | None] = mapped_column(String(500))
    custom4: Mapped[str | None] = mapped_column(String(500))
    custom5: Mapped[str | None] = mapped_column(String(500))
    is_suppressed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships: Mapped[list["ContactListMember"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan"
    )


class ContactListMember(Base):
    __tablename__ = "contact_list_members"
    __table_args__ = (PrimaryKeyConstraint("list_id", "contact_id"),)

    list_id: Mapped[int] = mapped_column(Integer, ForeignKey("contact_lists.id"))
    contact_id: Mapped[int] = mapped_column(Integer, ForeignKey("contacts.id"))

    contact_list: Mapped["ContactList"] = relationship(back_populates="members")
    contact: Mapped["Contact"] = relationship(back_populates="memberships")


class SuppressionList(Base):
    __tablename__ = "suppression_list"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(200))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
