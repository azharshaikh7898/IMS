from __future__ import annotations

from dataclasses import dataclass
from app.models.schemas import Severity


@dataclass(frozen=True, slots=True)
class AlertDecision:
    route: str
    escalation_minutes: int
    notify_executives: bool


class AlertStrategy:
    def decide(self, severity: Severity) -> AlertDecision:
        raise NotImplementedError


class P0AlertStrategy(AlertStrategy):
    def decide(self, severity: Severity) -> AlertDecision:
        return AlertDecision(route="pagerduty:oncall,slack:war-room,email:leadership", escalation_minutes=5, notify_executives=True)


class P1AlertStrategy(AlertStrategy):
    def decide(self, severity: Severity) -> AlertDecision:
        return AlertDecision(route="pagerduty:oncall,slack:team", escalation_minutes=15, notify_executives=False)


class P2AlertStrategy(AlertStrategy):
    def decide(self, severity: Severity) -> AlertDecision:
        return AlertDecision(route="slack:team", escalation_minutes=30, notify_executives=False)


STRATEGIES: dict[Severity, AlertStrategy] = {
    Severity.P0: P0AlertStrategy(),
    Severity.P1: P1AlertStrategy(),
    Severity.P2: P2AlertStrategy(),
}


def choose_alert_strategy(severity: Severity) -> AlertDecision:
    return STRATEGIES[severity].decide(severity)
