"""Token-bucket rate limiter for send throttling."""
import time
import threading


class ThrottleService:
    def __init__(self, delay_seconds: float = 1.0, hourly_limit: int = 100):
        self.delay = delay_seconds
        self.hourly_limit = hourly_limit
        self._lock = threading.Lock()
        self._hour_start = time.time()
        self._hour_count = 0
        self._last_send = 0.0

    def wait(self):
        with self._lock:
            now = time.time()

            # reset hourly counter
            if now - self._hour_start >= 3600:
                self._hour_start = now
                self._hour_count = 0

            # block until hourly limit frees up
            while self._hour_count >= self.hourly_limit:
                wait = 3600 - (time.time() - self._hour_start)
                if wait > 0:
                    time.sleep(min(wait, 30))
                now = time.time()
                if now - self._hour_start >= 3600:
                    self._hour_start = now
                    self._hour_count = 0

            # enforce per-send delay
            elapsed = time.time() - self._last_send
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)

            self._last_send = time.time()
            self._hour_count += 1
