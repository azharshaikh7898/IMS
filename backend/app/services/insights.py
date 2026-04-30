from __future__ import annotations

from collections import Counter
from typing import Iterable
from app.models.schemas import Severity


class RCAInsightService:
    def suggest_category(self, incident_titles: Iterable[str]) -> str:
        tokens = Counter()
        for title in incident_titles:
            tokens.update(token.lower() for token in title.split())
        if not tokens:
            return "unknown"
        return tokens.most_common(1)[0][0]


class EscalationService:
    def next_severity(self, current: Severity, signal_rate_per_minute: float) -> Severity:
        if current == Severity.P2 and signal_rate_per_minute > 20:
            return Severity.P1
        if current == Severity.P1 and signal_rate_per_minute > 50:
            return Severity.P0
        return current
