from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from app.models.schemas import IncidentStatus, RCARequest, Severity


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, object] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.channels: list[tuple[str, dict[str, object]]] = []

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value, ex: int | None = None, nx: bool = False):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    async def delete(self, key: str):
        self.store.pop(key, None)

    async def incr(self, key: str):
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = value
        return value

    async def expire(self, key: str, ttl: int):
        return True

    async def ping(self):
        return True

    async def publish(self, channel: str, payload: str):
        self.channels.append((channel, {"payload": payload}))

    async def xadd(self, stream: str, payload: dict[str, str], maxlen: int | None = None, approximate: bool = False):
        event_id = str(uuid4())
        self.streams.setdefault(stream, []).append((event_id, payload))
        return event_id

    async def xgroup_create(self, stream: str, group: str, id: str = "0-0", mkstream: bool = False):
        return True

    async def xreadgroup(self, group: str, consumer: str, streams: dict[str, str], count: int = 100, block: int = 5000):
        results = []
        for stream_name, start in streams.items():
            events = self.streams.get(stream_name, [])
            if events:
                results.append((stream_name, events[:count]))
                self.streams[stream_name] = events[count:]
        return results

    async def xack(self, stream: str, group: str, event_id: str):
        return 1

    async def zadd(self, key: str, payload: dict[str, float]):
        bucket = self.store.setdefault(key, {})
        bucket.update(payload)

    async def zrevrange(self, key: str, start: int, stop: int):
        bucket = self.store.get(key, {})
        return list(bucket.keys())[start:stop + 1]

    def pubsub(self):
        return SimpleNamespace(subscribe=lambda *args, **kwargs: None, get_message=lambda **kwargs: None, unsubscribe=lambda *args, **kwargs: None, close=lambda: None)


class FakeCacheRepository:
    def __init__(self, redis: FakeRedis) -> None:
        self.redis = redis

    async def publish_dashboard_event(self, channel: str, payload: dict):
        await self.redis.publish(channel, payload)

    async def set_json(self, key: str, value: dict, ttl_seconds: int | None = None):
        self.redis.store[key] = value

    async def get_json(self, key: str):
        value = self.redis.store.get(key)
        return value if isinstance(value, dict) else None

    async def add_to_sorted_set(self, key: str, score: float, member: str):
        await self.redis.zadd(key, {member: score})

    async def get_sorted_set(self, key: str, start: int = 0, stop: int = 100):
        return await self.redis.zrevrange(key, start, stop)

    async def acquire_lock(self, key: str, value: str, ttl_seconds: int = 5):
        return await self.redis.set(key, value, nx=True)

    async def release_lock(self, key: str, value: str):
        if self.redis.store.get(key) == value:
            await self.redis.delete(key)


@dataclass
class FakeIncident:
    id: str
    component_id: str
    severity: Severity
    status: IncidentStatus = IncidentStatus.OPEN
    title: str = ""
    summary: str = ""
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    mttr_seconds: float | None = None
    signal_count: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FakeIncidentRepository:
    def __init__(self) -> None:
        self.incidents: dict[str, FakeIncident] = {}
        self.rca: dict[str, RCARequest] = {}
        self.links: list[tuple[str, str, str]] = []

    async def create_incident(self, *, incident_id: str, component_id: str, severity: Severity, title: str, summary: str, opened_at: datetime):
        incident = FakeIncident(id=incident_id, component_id=component_id, severity=severity, title=title, summary=summary, opened_at=opened_at, signal_count=1)
        self.incidents[incident_id] = incident
        return incident

    async def get_incident(self, incident_id: str):
        return self.incidents.get(incident_id)

    async def list_incidents(self, limit: int = 100):
        return list(self.incidents.values())[:limit]

    async def increment_signal_count(self, incident_id: str, amount: int = 1):
        self.incidents[incident_id].signal_count += amount

    async def update_status(self, incident_id: str, status: IncidentStatus, resolved_at: datetime | None = None, closed_at: datetime | None = None, mttr_seconds: float | None = None):
        incident = self.incidents[incident_id]
        incident.status = status
        incident.resolved_at = resolved_at or incident.resolved_at
        incident.closed_at = closed_at or incident.closed_at
        incident.mttr_seconds = mttr_seconds
        incident.updated_at = datetime.now(timezone.utc)
        return incident

    async def attach_rca(self, incident_id: str, rca: RCARequest):
        self.rca[incident_id] = rca
        return rca

    async def link_signal(self, incident_id: str, signal_id: str, component_id: str):
        self.links.append((incident_id, signal_id, component_id))

    async def get_rca(self, incident_id: str):
        return self.rca.get(incident_id)


class FakeSignalRepository:
    def __init__(self) -> None:
        self.signals: dict[str, dict] = {}
        self.links: list[tuple[str, str]] = []

    async def insert_signal(self, signal: dict):
        self.signals[signal["signal_id"]] = signal
        return signal

    async def link_signal_to_incident(self, signal_id: str, incident_id: str):
        self.links.append((signal_id, incident_id))
        if signal_id not in self.signals:
            self.signals[signal_id] = {"signal_id": signal_id}
        self.signals[signal_id]["incident_id"] = incident_id

    async def list_signals_for_incident(self, incident_id: str, limit: int = 100):
        return [signal for signal in self.signals.values() if signal.get("incident_id") == incident_id][:limit]


class FakeRealtimeHub:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def start(self):
        return None

    async def stop(self):
        return None

    def register_listener(self):
        raise NotImplementedError

    def unregister_listener(self, queue):
        return None

    async def publish(self, payload: dict):
        self.events.append(payload)


class FakeLimiter:
    async def allow(self, identifier: str):
        return SimpleNamespace(allowed=True, remaining=999, reset_in_seconds=60)


class FakeServiceContainer(SimpleNamespace):
    pass
