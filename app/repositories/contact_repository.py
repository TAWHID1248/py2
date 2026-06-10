from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.contact import Contact, ContactList, ContactListMember, SuppressionList


class ContactRepository:
    def __init__(self, session: Session):
        self.session = session

    # --- lists ---

    def all_lists(self) -> list[ContactList]:
        return self.session.query(ContactList).order_by(ContactList.name).all()

    def get_list(self, list_id: int) -> ContactList | None:
        return self.session.get(ContactList, list_id)

    def get_list_by_name(self, name: str) -> ContactList | None:
        return self.session.query(ContactList).filter_by(name=name).first()

    def create_list(self, name: str, description: str = "") -> ContactList:
        cl = ContactList(name=name, description=description)
        self.session.add(cl)
        self.session.flush()
        return cl

    def delete_list(self, list_id: int) -> bool:
        cl = self.get_list(list_id)
        if not cl:
            return False
        self.session.delete(cl)
        self.session.flush()
        return True

    # --- contacts ---

    def get_contact(self, contact_id: int) -> Contact | None:
        return self.session.get(Contact, contact_id)

    def get_by_email(self, email: str) -> Contact | None:
        return self.session.query(Contact).filter_by(email=email.lower().strip()).first()

    def contacts_in_list(self, list_id: int) -> list[Contact]:
        return (
            self.session.query(Contact)
            .join(ContactListMember, ContactListMember.contact_id == Contact.id)
            .filter(ContactListMember.list_id == list_id)
            .filter(Contact.is_suppressed.is_(False))
            .all()
        )

    def upsert_contact(self, data: dict) -> tuple[Contact, bool]:
        """Return (contact, created). Deduplicates on email."""
        email = data["email"].lower().strip()
        existing = self.get_by_email(email)
        if existing:
            for k, v in data.items():
                if k != "email" and v:
                    setattr(existing, k, v)
            self.session.flush()
            return existing, False
        c = Contact(**{**data, "email": email})
        self.session.add(c)
        self.session.flush()
        return c, True

    def add_to_list(self, list_id: int, contact_id: int):
        exists = (
            self.session.query(ContactListMember)
            .filter_by(list_id=list_id, contact_id=contact_id)
            .first()
        )
        if not exists:
            self.session.add(ContactListMember(list_id=list_id, contact_id=contact_id))
            self.session.flush()
            self._refresh_count(list_id)

    def _refresh_count(self, list_id: int):
        count = (
            self.session.query(func.count(ContactListMember.contact_id))
            .filter_by(list_id=list_id)
            .scalar()
        )
        cl = self.get_list(list_id)
        if cl:
            cl.record_count = count
            self.session.flush()

    # --- suppression ---

    def is_suppressed(self, email: str) -> bool:
        email = email.lower().strip()
        return (
            self.session.query(SuppressionList).filter_by(email=email).first() is not None
        )

    def suppress(self, email: str, reason: str = ""):
        email = email.lower().strip()
        if not self.is_suppressed(email):
            self.session.add(SuppressionList(email=email, reason=reason))
            self.session.flush()
        contact = self.get_by_email(email)
        if contact:
            contact.is_suppressed = True
            self.session.flush()

    def all_suppressed(self) -> list[SuppressionList]:
        return self.session.query(SuppressionList).order_by(SuppressionList.email).all()
