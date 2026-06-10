from sqlalchemy.orm import Session
from app.models.account import Account
from app.core.crypto import encrypt, decrypt


class AccountRepository:
    def __init__(self, session: Session):
        self.session = session

    def all(self) -> list[Account]:
        return self.session.query(Account).order_by(Account.name).all()

    def get(self, account_id: int) -> Account | None:
        return self.session.get(Account, account_id)

    def get_by_email(self, email: str) -> Account | None:
        return self.session.query(Account).filter_by(email=email).first()

    def active(self) -> list[Account]:
        return self.session.query(Account).filter_by(is_active=True).all()

    def create(self, data: dict) -> Account:
        if "smtp_password" in data:
            data["smtp_password_enc"] = encrypt(data.pop("smtp_password"))
        if "oauth_token" in data:
            data["oauth_token_enc"] = encrypt(data.pop("oauth_token"))
        acc = Account(**data)
        self.session.add(acc)
        self.session.flush()
        return acc

    def update(self, account_id: int, data: dict) -> Account | None:
        acc = self.get(account_id)
        if not acc:
            return None
        if "smtp_password" in data:
            data["smtp_password_enc"] = encrypt(data.pop("smtp_password"))
        if "oauth_token" in data:
            data["oauth_token_enc"] = encrypt(data.pop("oauth_token"))
        for k, v in data.items():
            setattr(acc, k, v)
        self.session.flush()
        return acc

    def delete(self, account_id: int) -> bool:
        acc = self.get(account_id)
        if not acc:
            return False
        self.session.delete(acc)
        self.session.flush()
        return True

    def get_smtp_password(self, acc: Account) -> str | None:
        if acc.smtp_password_enc:
            return decrypt(acc.smtp_password_enc)
        return None
