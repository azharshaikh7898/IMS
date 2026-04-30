from __future__ import annotations

import time
from dataclasses import dataclass
from app.repositories.redis_repo import CacheRepository


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    reset_in_seconds: int


class RedisRateLimiter:
    def __init__(self, cache: CacheRepository, limit_per_minute: int) -> None:
        self.cache = cache
        self.limit_per_minute = limit_per_minute

    async def allow(self, identifier: str) -> RateLimitDecision:
        window = int(time.time() // 60)
        key = f"rate:{identifier}:{window}"
        current = await self.cache.redis.get(key)
        count = int(current or 0)
        if count >= self.limit_per_minute:
            return RateLimitDecision(False, 0, 60 - int(time.time() % 60))
        await self.cache.redis.incr(key)
        await self.cache.redis.expire(key, 70)
        return RateLimitDecision(True, self.limit_per_minute - count - 1, 60 - int(time.time() % 60))
