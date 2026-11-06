import time
from collections import deque
from dataclasses import dataclass, field

from app.errors import ApiError


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("rate limit exceeded")


@dataclass
class InMemoryRateLimiter:
    """Fixed-window counter suitable for a single process.

    Phase 1 defaults to this backend; production uses Redis (see services/ratelimit
    in a later phase) so limits survive restarts and multiple workers.
    """

    limit: int
    window_seconds: int
    _hits: dict[str, deque[float]] = field(default_factory=dict)

    def check(self, key: str) -> None:
        now = time.monotonic()
        bucket = self._hits.setdefault(key, deque())
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
            raise RateLimitExceeded(retry_after)
        bucket.append(now)

    def reset(self) -> None:
        self._hits.clear()


def enforce(limiter: InMemoryRateLimiter, key: str) -> None:
    try:
        limiter.check(key)
    except RateLimitExceeded as exc:
        raise ApiError(
            429,
            "rate_limited",
            "Terlalu banyak percobaan. Coba lagi sebentar.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
