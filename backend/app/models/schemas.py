from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class RCARequest(BaseModel):
    root_cause_category: str = Field(min_length=3, max_length=120)
    root_cause_summary: str = Field(min_length=10, max_length=1000)
    fix_description: str = Field(min_length=10, max_length=1000)
    prevention_plan: str = Field(min_length=10, max_length=1000)
    occurred_at: datetime
    detected_at: datetime

    @field_validator("detected_at")
    @classmethod
    def detected_not_before_occurred(cls, value: datetime, info: Any) -> datetime:
        occurred_at = info.data.get("occurred_at")
        if occurred_at and value < occurred_at:
            raise ValueError("detected_at must not be earlier than occurred_at")
        return value


class SignalIngestRequest(BaseModel):
    component_id: str = Field(min_length=1, max_length=120)
    severity: Severity
    source: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=5, max_length=300)
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class SignalAcceptedResponse(BaseModel):
    signal_id: str
    component_id: str
    queued: bool = True


class IncidentTransitionRequest(BaseModel):
    target_status: IncidentStatus
    notes: str | None = None


class IncidentSummary(BaseModel):
    id: str
    component_id: str
    severity: Severity
    status: IncidentStatus
    title: str
    opened_at: datetime
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    mttr_seconds: float | None = None
    signal_count: int = 0
    root_cause_category: str | None = None
    updated_at: datetime


class IncidentDetail(IncidentSummary):
    raw_signals: list[dict[str, Any]] = Field(default_factory=list)
    rca: RCARequest | None = None
    state_transitions: list["StateTransitionEvent"] = Field(default_factory=list)


class StateTransitionEvent(BaseModel):
    id: int
    incident_id: str
    new_status: IncidentStatus
    transitioned_at: datetime
    triggered_by: str
    notes: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, bool]


class DashboardEvent(BaseModel):
    event_type: str
    incident: IncidentSummary
