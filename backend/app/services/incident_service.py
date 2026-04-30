from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from app.models.schemas import IncidentDetail, IncidentStatus, IncidentSummary, RCARequest, SignalIngestRequest, Severity, StateTransitionEvent
from app.repositories.mongo_repo import SignalRepository
from app.repositories.redis_repo import CacheRepository
from app.repositories.sql_repo import IncidentRepository
from app.models.sql import IncidentStatusEnum
from app.services.alerting import choose_alert_strategy
from app.services.mttr import calculate_mttr_seconds
from app.services.workflow import IncidentContext, has_valid_rca, validate_transition
from app.services.realtime import RealtimeHub


class IncidentService:
    def __init__(self, incidents: IncidentRepository, signals: SignalRepository, cache: CacheRepository, realtime: RealtimeHub) -> None:
        self._incidents = incidents
        self._signals = signals
        self._cache = cache
        self._realtime = realtime

    async def ingest_signal(self, payload: SignalIngestRequest, signal_id: str) -> dict[str, Any]:
        document = {
            "signal_id": signal_id,
            "component_id": payload.component_id,
            "severity": payload.severity.value,
            "source": payload.source,
            "summary": payload.summary,
            "payload": payload.payload,
            "occurred_at": payload.occurred_at or datetime.now(timezone.utc),
            "ingested_at": datetime.now(timezone.utc),
        }
        await self._signals.insert_signal(document)
        await self._cache.redis.xadd("ims:signals", {"signal_id": signal_id, "component_id": payload.component_id, "severity": payload.severity.value, "summary": payload.summary}, maxlen=50000, approximate=True)
        await self._cache.redis.incr("metrics:signals_5s")
        return document

    async def list_incidents(self, limit: int = 100) -> list[IncidentSummary]:
        incidents = await self._incidents.list_incidents(limit=limit)
        return [self._to_summary(incident) for incident in incidents]

    async def get_incident(self, incident_id: str) -> IncidentDetail | None:
        incident = await self._incidents.get_incident(incident_id)
        if incident is None:
            return None
        signals = await self._signals.list_signals_for_incident(incident_id)
        rca = await self._incidents.get_rca(incident_id)
        transitions = await self._incidents.get_state_transitions(incident_id)
        transition_events = [
            StateTransitionEvent(
                id=t.id,
                incident_id=t.incident_id,
                new_status=IncidentStatus(t.new_status.value),
                transitioned_at=t.transitioned_at,
                triggered_by=t.triggered_by,
                notes=t.notes
            )
            for t in transitions
        ]
        return IncidentDetail(**self._to_summary(incident).model_dump(), raw_signals=signals, rca=self._rca_to_request(rca) if rca else None, state_transitions=transition_events)

    async def transition_incident(self, incident_id: str, target_status: IncidentStatus, notes: str | None = None) -> IncidentSummary:
        incident = await self._incidents.get_incident(incident_id)
        if incident is None:
            raise KeyError(incident_id)
        rca = await self._incidents.get_rca(incident_id)
        context = IncidentContext(status=IncidentStatus(incident.status.value), root_cause_present=has_valid_rca(self._rca_to_request(rca) if rca else None), resolved_at=incident.resolved_at, closed_at=incident.closed_at)
        validate_transition(context, target_status)
        resolved_at = context.resolved_at if target_status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED} else incident.resolved_at
        closed_at = context.closed_at if target_status == IncidentStatus.CLOSED else incident.closed_at
        mttr_seconds = calculate_mttr_seconds(incident.opened_at, closed_at)
        updated = await self._incidents.update_status(incident_id, target_status, resolved_at=resolved_at, closed_at=closed_at, mttr_seconds=mttr_seconds)
        if updated is None:
            raise KeyError(incident_id)
        await self._incidents.record_state_transition(incident_id, IncidentStatusEnum(target_status.value), triggered_by="system", notes=notes)
        summary = self._to_summary(updated)
        await self._realtime.publish({"event_type": "incident.updated", "incident": summary.model_dump()})
        return summary

    async def submit_rca(self, incident_id: str, rca: RCARequest) -> IncidentSummary:
        incident = await self._incidents.get_incident(incident_id)
        if incident is None:
            raise KeyError(incident_id)
        await self._incidents.attach_rca(incident_id, rca)
        summary = self._to_summary(incident)
        summary.root_cause_category = rca.root_cause_category
        await self._realtime.publish({"event_type": "incident.rca", "incident": summary.model_dump()})
        return summary

    async def close_incident(self, incident_id: str) -> IncidentSummary:
        incident = await self._incidents.get_incident(incident_id)
        if incident is None:
            raise KeyError(incident_id)
        rca = await self._incidents.get_rca(incident_id)
        if not has_valid_rca(self._rca_to_request(rca) if rca else None):
            raise ValueError("RCA is required before closing an incident")
        return await self.transition_incident(incident_id, IncidentStatus.CLOSED)

    def _to_summary(self, incident) -> IncidentSummary:
        return IncidentSummary(
            id=incident.id,
            component_id=incident.component_id,
            severity=Severity(incident.severity.value),
            status=IncidentStatus(incident.status.value),
            title=incident.title,
            opened_at=incident.opened_at,
            resolved_at=incident.resolved_at,
            closed_at=incident.closed_at,
            mttr_seconds=incident.mttr_seconds,
            signal_count=incident.signal_count,
            root_cause_category=None,
            updated_at=incident.updated_at,
        )

    def _rca_to_request(self, rca) -> RCARequest | None:
        if rca is None:
            return None
        return RCARequest(
            root_cause_category=rca.root_cause_category,
            root_cause_summary=rca.root_cause_summary,
            fix_description=rca.fix_description,
            prevention_plan=rca.prevention_plan,
            occurred_at=rca.occurred_at,
            detected_at=rca.detected_at,
        )
