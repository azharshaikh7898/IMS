from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from app.models.schemas import IncidentStatus, RCARequest


class InvalidTransitionError(ValueError):
    pass


@dataclass(slots=True)
class IncidentContext:
    status: IncidentStatus
    root_cause_present: bool = False
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class IncidentState(Protocol):
    name: IncidentStatus

    def transition(self, context: IncidentContext, target: IncidentStatus) -> IncidentContext: ...


class _BaseState:
    allowed: set[IncidentStatus] = set()
    name: IncidentStatus

    def transition(self, context: IncidentContext, target: IncidentStatus) -> IncidentContext:
        if target not in self.allowed:
            raise InvalidTransitionError(f"{self.name.value} cannot transition to {target.value}")
        return context


class OpenState(_BaseState):
    name = IncidentStatus.OPEN
    allowed = {IncidentStatus.INVESTIGATING, IncidentStatus.RESOLVED}


class InvestigatingState(_BaseState):
    name = IncidentStatus.INVESTIGATING
    allowed = {IncidentStatus.RESOLVED}


class ResolvedState(_BaseState):
    name = IncidentStatus.RESOLVED
    allowed = {IncidentStatus.CLOSED}

    def transition(self, context: IncidentContext, target: IncidentStatus) -> IncidentContext:
        if target == IncidentStatus.CLOSED and not context.root_cause_present:
            raise InvalidTransitionError("Closing an incident requires a valid RCA")
        return super().transition(context, target)


class ClosedState(_BaseState):
    name = IncidentStatus.CLOSED
    allowed: set[IncidentStatus] = set()

    def transition(self, context: IncidentContext, target: IncidentStatus) -> IncidentContext:
        raise InvalidTransitionError("Closed incidents are immutable")


STATE_MAP: dict[IncidentStatus, IncidentState] = {
    IncidentStatus.OPEN: OpenState(),
    IncidentStatus.INVESTIGATING: InvestigatingState(),
    IncidentStatus.RESOLVED: ResolvedState(),
    IncidentStatus.CLOSED: ClosedState(),
}


def validate_transition(context: IncidentContext, target: IncidentStatus) -> IncidentContext:
    state = STATE_MAP[context.status]
    updated = state.transition(context, target)
    updated.status = target
    if target == IncidentStatus.RESOLVED and updated.resolved_at is None:
        updated.resolved_at = datetime.now(timezone.utc)
    if target == IncidentStatus.CLOSED and updated.closed_at is None:
        updated.closed_at = datetime.now(timezone.utc)
    return updated


def has_valid_rca(rca: RCARequest | None) -> bool:
    return bool(rca and rca.root_cause_category.strip() and rca.root_cause_summary.strip())
