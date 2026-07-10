from __future__ import annotations

from app.limiter import InMemoryRateLimiter


def get_stats(limiter: InMemoryRateLimiter) -> dict[str, object]:
    return limiter.stats()
