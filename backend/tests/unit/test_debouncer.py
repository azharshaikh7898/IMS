from datetime import datetime, timezone
import pytest
from app.models.schemas import Severity, SignalIngestRequest
from app.services.debouncer import DebouncerService
from tests.fakes import FakeCacheRepository, FakeIncidentRepository, FakeRealtimeHub, FakeRedis, FakeSignalRepository


@pytest.mark.asyncio
async def test_debouncer_groups_signals_by_component():
    redis = FakeRedis()
    cache = FakeCacheRepository(redis)
    incidents = FakeIncidentRepository()
    signals = FakeSignalRepository()
    realtime = FakeRealtimeHub()
    debouncer = DebouncerService(incidents, signals, cache, realtime, debounce_seconds=10)

    payload = SignalIngestRequest(component_id="payments-api", severity=Severity.P0, source="pagerduty", summary="db timeout")
    first = await debouncer.process_signal(payload, "sig-1")
    second = await debouncer.process_signal(payload, "sig-2")

    assert first.created is True
    assert second.created is False
    assert len(incidents.incidents) == 1
    incident = next(iter(incidents.incidents.values()))
    assert incident.signal_count == 2
    assert signals.signals["sig-1"]["incident_id"] == incident.id
    assert signals.signals["sig-2"]["incident_id"] == incident.id
    assert realtime.events[0]["event_type"] == "incident.created"
