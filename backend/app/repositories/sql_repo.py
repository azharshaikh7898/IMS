from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.models.sql import Incident, IncidentMetric, IncidentSignalLink, IncidentStateTransition, IncidentStatusEnum, RCA, SeverityEnum
from app.models.schemas import IncidentStatus, RCARequest, Severity
from app.services.mttr import calculate_mttr_seconds


class IncidentRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create_incident(self, *, incident_id: str, component_id: str, severity: Severity, title: str, summary: str, opened_at: datetime) -> Incident:
        incident = Incident(
            id=incident_id,
            component_id=component_id,
            severity=SeverityEnum(severity.value),
            status=IncidentStatusEnum.OPEN,
            title=title,
            summary=summary,
            opened_at=opened_at,
            signal_count=1,
        )
        async with self._session_factory() as session:
            session.add(incident)
            await session.commit()
            await session.refresh(incident)
            return incident

    async def get_incident(self, incident_id: str) -> Incident | None:
        async with self._session_factory() as session:
            return await session.get(Incident, incident_id)

    async def list_incidents(self, limit: int = 100) -> list[Incident]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Incident).options(selectinload(Incident.rca)).order_by(Incident.updated_at.desc()).limit(limit)
            )
            return list(result.scalars().all())

    async def increment_signal_count(self, incident_id: str, amount: int = 1) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(Incident).where(Incident.id == incident_id).values(signal_count=Incident.signal_count + amount)
            )
            await session.commit()

    async def update_status(self, incident_id: str, status: IncidentStatus, resolved_at: datetime | None = None, closed_at: datetime | None = None, mttr_seconds: float | None = None) -> Incident | None:
        async with self._session_factory() as session:
            incident = await session.get(Incident, incident_id)
            if incident is None:
                return None
            incident.status = IncidentStatusEnum(status.value)
            if resolved_at is not None:
                incident.resolved_at = resolved_at
            if closed_at is not None:
                incident.closed_at = closed_at
            if mttr_seconds is not None:
                incident.mttr_seconds = mttr_seconds
            await session.commit()
            await session.refresh(incident)
            return incident

    async def attach_rca(self, incident_id: str, rca: RCARequest) -> RCA:
        async with self._session_factory() as session:
            incident = await session.get(Incident, incident_id)
            if incident is None:
                raise KeyError(incident_id)
            record = RCA(
                incident_id=incident_id,
                root_cause_category=rca.root_cause_category,
                root_cause_summary=rca.root_cause_summary,
                fix_description=rca.fix_description,
                prevention_plan=rca.prevention_plan,
                occurred_at=rca.occurred_at,
                detected_at=rca.detected_at,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def link_signal(self, incident_id: str, signal_id: str, component_id: str) -> None:
        async with self._session_factory() as session:
            session.add(IncidentSignalLink(incident_id=incident_id, signal_id=signal_id, component_id=component_id))
            await session.commit()

    async def save_metric(self, name: str, value: float, bucket_ts: datetime, tags: dict[str, str] | None = None) -> None:
        async with self._session_factory() as session:
            session.add(IncidentMetric(metric_name=name, metric_value=value, bucket_ts=bucket_ts, tags=tags or {}))
            await session.commit()

    async def get_signal_count(self, incident_id: str) -> int:
        incident = await self.get_incident(incident_id)
        return incident.signal_count if incident else 0

    async def get_rca(self, incident_id: str) -> RCA | None:
        async with self._session_factory() as session:
            result = await session.execute(select(RCA).where(RCA.incident_id == incident_id))
            return result.scalar_one_or_none()

    async def record_state_transition(self, incident_id: str, new_status: IncidentStatusEnum, triggered_by: str = "system", notes: str | None = None) -> IncidentStateTransition:
        async with self._session_factory() as session:
            transition = IncidentStateTransition(
                incident_id=incident_id,
                new_status=new_status,
                triggered_by=triggered_by,
                notes=notes
            )
            session.add(transition)
            await session.commit()
            await session.refresh(transition)
            return transition

    async def get_state_transitions(self, incident_id: str) -> list[IncidentStateTransition]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(IncidentStateTransition)
                .where(IncidentStateTransition.incident_id == incident_id)
                .order_by(IncidentStateTransition.transitioned_at)
            )
            return list(result.scalars().all())
