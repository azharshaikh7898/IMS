from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from typing import Any
from redis.asyncio import Redis


class RealtimeHub:
    def __init__(self, redis: Redis, channel: str = "ims:dashboard") -> None:
        self.redis = redis
        self.channel = channel
        self._listeners: set[asyncio.Queue[dict[str, Any]]] = set()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._forward_events())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task

    def register_listener(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._listeners.add(queue)
        return queue

    def unregister_listener(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._listeners.discard(queue)

    async def publish(self, payload: dict[str, Any]) -> None:
        await self.redis.publish(self.channel, json.dumps(payload, default=str))

    async def _forward_events(self) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.channel)
        try:
            while not self._stop.is_set():
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    await asyncio.sleep(0.1)
                    continue
                raw = message.get("data")
                if not raw:
                    continue
                event = json.loads(raw)
                for queue in list(self._listeners):
                    if queue.full():
                        continue
                    queue.put_nowait(event)
        finally:
            await pubsub.unsubscribe(self.channel)
            await pubsub.close()
