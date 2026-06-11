"""Round-robin multi-account pool with per-account throttle tracking."""
import threading
from app.models.account import Account
from app.core.logger import get_logger

log = get_logger(__name__)


class AccountRotationService:
    def __init__(self, accounts: list[Account]):
        if not accounts:
            raise ValueError("Account pool is empty")
        self._accounts = accounts
        self._index = 0
        self._lock = threading.Lock()
        self._sent_counts: dict[int, int] = {a.id: 0 for a in accounts}

    def next_account(self) -> Account:
        """Return next available account in round-robin order."""
        with self._lock:
            # Skip accounts that hit their daily limit
            start = self._index
            while True:
                acc = self._accounts[self._index]
                self._index = (self._index + 1) % len(self._accounts)
                if self._sent_counts[acc.id] < acc.daily_limit:
                    return acc
                if self._index == start:
                    raise RuntimeError("All accounts have hit their daily send limit")

    def record_send(self, account_id: int):
        with self._lock:
            self._sent_counts[account_id] = self._sent_counts.get(account_id, 0) + 1

    def stats(self) -> list[dict]:
        return [
            {"account_id": acc.id, "email": acc.email,
             "sent": self._sent_counts.get(acc.id, 0), "limit": acc.daily_limit}
            for acc in self._accounts
        ]
