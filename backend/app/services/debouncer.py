from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
from app.models.schemas import SignalIngestRequest, Severity
from app.repositories.mongo_repo import SignalRepository
from app.repositories.redis_repo import CacheRepository
from app.repositories.sql_repo import IncidentRepository
from app.services.alerting import choose_alert_strategy
from app.services.realtime import RealtimeHub


@dataclass(slots=True)
class DebounceResult:
    incident_id: str
    created: bool


class ComponentLockManager:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def lock_for(self, component_id: str) -> asyncio.Lock:
        async with self._guard:
            lock = self._locks.get(component_id)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[component_id] = lock
            return lock


class DebouncerService:
    def __init__(self, incidents: IncidentRepository, signals: SignalRepository, cache: CacheRepository, realtime: RealtimeHub, debounce_seconds: int) -> None:
        self._incidents = incidents
        self._signals = signals
        self._cache = cache
        self._realtime = realtime
        self._debounce_seconds = debounce_seconds
        self._locks = ComponentLockManager()

    def _incident_key(self, component_id: str) -> str:
        return f"debounce:incident:{component_id}"

    def _lock_key(self, component_id: str) -> str:
        return f"debounce:lock:{component_id}"

    async def process_signal(self, payload: SignalIngestRequest, signal_id: str) -> DebounceResult:
        lock = await self._locks.lock_for(payload.component_id)
        async with lock:
            existing = await self._cache.get_json(self._incident_key(payload.component_id))
            if existing and existing.get("incident_id"):
                incident_id = existing["incident_id"]
                await self._signals.link_signal_to_incident(signal_id, incident_id)
                await self._incidents.link_signal(incident_id, signal_id, payload.component_id)
                await self._incidents.increment_signal_count(incident_id)
                return DebounceResult(incident_id=incident_id, created=False)

            lock_value = str(uuid4())
            acquired = await self._cache.acquire_lock(self._lock_key(payload.component_id), lock_value, ttl_seconds=5)
            if not acquired:
                await asyncio.sleep(0.05)
                existing = await self._cache.get_json(self._incident_key(payload.component_id))
                if existing and existing.get("incident_id"):
                    incident_id = existing["incident_id"]
                    await self._signals.link_signal_to_incident(signal_id, incident_id)
                    await self._incidents.link_signal(incident_id, signal_id, payload.component_id)
                    await self._incidents.increment_signal_count(incident_id)
                    return DebounceResult(incident_id=incident_id, created=False)
                raise RuntimeError("Unable to acquire debounce lease")

            try:
                incident_id = str(uuid4())
                opened_at = payload.occurred_at or datetime.now(timezone.utc)
                title = f"{payload.component_id} {payload.severity.value} signal"
                await self._incidents.create_incident(
                    incident_id=incident_id,
                    component_id=payload.component_id,
                    severity=payload.severity,
                    title=title,
                    summary=payload.summary,
                    opened_at=opened_at,
                )
                await self._cache.set_json(
                    self._incident_key(payload.component_id),
                    {"incident_id": incident_id, "component_id": payload.component_id, "severity": payload.severity.value},
                    ttl_seconds=self._debounce_seconds,
                )
                await self._signals.link_signal_to_incident(signal_id, incident_id)
                await self._incidents.link_signal(incident_id, signal_id, payload.component_id)
                incident = await self._incidents.get_incident(incident_id)
                if incident:
                    alert_decision = choose_alert_strategy(payload.severity)
                    await self._realtime.publish({"event_type": "incident.created", "incident": {"id": incident.id, "component_id": incident.component_id, "severity": incident.severity.value, "status": incident.status.value, "title": incident.title, "opened_at": incident.opened_at, "resolved_at": incident.resolved_at, "closed_at": incident.closed_at, "mttr_seconds": incident.mttr_seconds, "signal_count": incident.signal_count, "root_cause_category": None, "updated_at": incident.updated_at, "alert_route": alert_decision.route}})
                return DebounceResult(incident_id=incident_id, created=True)
            finally:
                await self._cache.release_lock(self._lock_key(payload.component_id), lock_value)
