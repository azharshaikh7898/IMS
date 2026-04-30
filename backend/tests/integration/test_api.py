from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.routes import router
from tests.fakes import FakeCacheRepository, FakeIncidentRepository, FakeLimiter, FakeRealtimeHub, FakeRedis, FakeServiceContainer, FakeSignalRepository
from app.api.deps import ServiceContainer
from app.services.debouncer import DebouncerService
from app.services.incident_service import IncidentService
from app.services.insights import RCAInsightService
from app.models.schemas import Severity, SignalIngestRequest, IncidentStatus, RCARequest
from datetime import datetime, timezone
import asyncio


def build_test_app() -> FastAPI:
    redis = FakeRedis()
    cache = FakeCacheRepository(redis)
    incidents = FakeIncidentRepository()
    signals = FakeSignalRepository()
    realtime = FakeRealtimeHub()
    incident_service = IncidentService(incidents, signals, cache, realtime)
    debouncer = DebouncerService(incidents, signals, cache, realtime, debounce_seconds=10)
    services = FakeServiceContainer(
        settings=None,
        incidents=incidents,
        signals=signals,
        cache=cache,
        realtime=realtime,
        limiter=FakeLimiter(),
        debouncer=debouncer,
        incident_service=incident_service,
        insights=RCAInsightService(),
    )
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.services = services
    return app


def test_signal_ingest_and_incident_lifecycle():
    app = build_test_app()
    client = TestClient(app)

    response = client.post(
        "/api/signals",
        json={"component_id": "checkout", "severity": "P1", "source": "pagerduty", "summary": "error spike", "payload": {}},
    )
    assert response.status_code == 202
    asyncio.run(
        app.state.services.debouncer.process_signal(
            SignalIngestRequest(component_id="checkout", severity=Severity.P1, source="pagerduty", summary="error spike", payload={}),
            response.json()["signal_id"],
        )
    )
    incident_id = next(iter(app.state.services.incidents.incidents))

    rca_response = client.post(
        f"/api/incidents/{incident_id}/rca",
        json={
            "root_cause_category": "Database",
            "root_cause_summary": "Connection pool exhaustion",
            "fix_description": "Resized pool",
            "prevention_plan": "Add alerts",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert rca_response.status_code == 200

    close_response = client.post(f"/api/incidents/{incident_id}/close")
    assert close_response.status_code == 200
    assert close_response.json()["status"] == IncidentStatus.CLOSED.value
