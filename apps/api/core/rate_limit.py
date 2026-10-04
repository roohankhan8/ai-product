import time
from collections import defaultdict, deque

from redis.asyncio import Redis

from core.config import get_settings


class InMemoryRateLimiter:
    """Small single-process limiter; use a shared store for multi-worker production."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        events = self._events[key]
        cutoff = now - window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        if len(self._events) > 10_000:
            self._events = {item: values for item, values in self._events.items() if values}
        return True


limiter = InMemoryRateLimiter()
redis_limiter = Redis.from_url(get_settings().redis_url, decode_responses=True)


async def allow_request(key: str, limit: int, window_seconds: int) -> bool:
    """Use shared Redis counters, falling back locally if Redis is unavailable."""
    redis_key = f"rate-limit:{key}"
    try:
        async with redis_limiter.pipeline(transaction=True) as pipeline:
            pipeline.incr(redis_key)
            pipeline.expire(redis_key, window_seconds)
            count, _ = await pipeline.execute()
        return int(count) <= limit
    except Exception:
        return limiter.allow(key, limit, window_seconds)
