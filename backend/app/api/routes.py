from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import text
from app.api.deps import ServiceContainer
from app.models.schemas import HealthResponse, IncidentStatus, IncidentTransitionRequest, RCARequest, SignalAcceptedResponse, SignalIngestRequest

router = APIRouter()


def get_services(request: Request) -> ServiceContainer:
    return request.app.state.services


@router.get("/health", response_model=HealthResponse)
async def health(services: ServiceContainer = Depends(get_services)) -> HealthResponse:
    checks = {"redis": False, "mongo": False, "postgres": False}
    try:
        await services.cache.redis.ping()
        checks["redis"] = True
    except Exception:
        pass
    try:
        await services.signals.collection.estimated_document_count()
        checks["mongo"] = True
    except Exception:
        pass
    try:
        async with services.incidents._session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = True
    except Exception:
        pass
    status_value = "ok" if all(checks.values()) else "degraded"
    return HealthResponse(status=status_value, checks=checks)


@router.post("/signals", response_model=SignalAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_signal(request: SignalIngestRequest, http_request: Request, services: ServiceContainer = Depends(get_services), x_request_id: str | None = Header(default=None)) -> SignalAcceptedResponse:
    remote = http_request.client.host if http_request.client else "unknown"
    rate = await services.limiter.allow(remote)
    if not rate.allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"retry_after": rate.reset_in_seconds})
    signal_id = x_request_id or str(uuid4())
    await services.incident_service.ingest_signal(request, signal_id)
    return SignalAcceptedResponse(signal_id=signal_id, component_id=request.component_id)


@router.get("/incidents")
async def list_incidents(limit: int = 100, services: ServiceContainer = Depends(get_services)):
    return [item.model_dump() for item in await services.incident_service.list_incidents(limit=limit)]


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, services: ServiceContainer = Depends(get_services)):
    incident = await services.incident_service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.model_dump()


@router.patch("/incidents/{incident_id}/status")
async def update_status(incident_id: str, payload: IncidentTransitionRequest, services: ServiceContainer = Depends(get_services)):
    try:
        updated = await services.incident_service.transition_incident(incident_id, payload.target_status, payload.notes)
        return updated.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/incidents/{incident_id}/rca")
async def create_rca(incident_id: str, payload: RCARequest, services: ServiceContainer = Depends(get_services)):
    try:
        incident = await services.incident_service.submit_rca(incident_id, payload)
        return incident.model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail="Incident not found")


@router.post("/incidents/{incident_id}/close")
async def close_incident(incident_id: str, services: ServiceContainer = Depends(get_services)):
    try:
        incident = await services.incident_service.close_incident(incident_id)
        return incident.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError:
        raise HTTPException(status_code=404, detail="Incident not found")


@router.get("/incidents/{incident_id}/insights")
async def incident_insights(incident_id: str, services: ServiceContainer = Depends(get_services)):
    incident = await services.incident_service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    historical = await services.incidents.list_incidents(limit=1000)
    related_titles = [item.title for item in historical if item.component_id == incident.component_id]
    return {
        "suggested_rca_category": services.insights.suggest_category(related_titles),
        "escalation": {
            "current_severity": incident.severity.value,
            "recommended_severity": services.insights.next_severity(incident.severity, incident.signal_count),
        },
    }
