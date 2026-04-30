from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from redis.asyncio import Redis


@dataclass(slots=True)
class DebounceLease:
    key: str
    incident_id: str
    ttl_seconds: int


class CacheRepository:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def publish_dashboard_event(self, channel: str, payload: dict[str, Any]) -> None:
        await self.redis.publish(channel, json.dumps(payload, default=str))

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
        serialized = json.dumps(value, default=str)
        if ttl_seconds:
            await self.redis.set(key, serialized, ex=ttl_seconds)
        else:
            await self.redis.set(key, serialized)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def add_to_sorted_set(self, key: str, score: float, member: str) -> None:
        await self.redis.zadd(key, {member: score})

    async def get_sorted_set(self, key: str, start: int = 0, stop: int = 100) -> list[str]:
        return list(await self.redis.zrevrange(key, start, stop))

    async def acquire_lock(self, key: str, value: str, ttl_seconds: int = 5) -> bool:
        return bool(await self.redis.set(key, value, ex=ttl_seconds, nx=True))

    async def release_lock(self, key: str, value: str) -> None:
        current = await self.redis.get(key)
        if current == value:
            await self.redis.delete(key)
