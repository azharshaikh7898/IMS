from __future__ import annotations

from datetime import datetime, timezone


def calculate_mttr_seconds(opened_at: datetime, closed_at: datetime | None) -> float | None:
    if closed_at is None:
        return None
    if opened_at.tzinfo is None:
        opened_at = opened_at.replace(tzinfo=timezone.utc)
    if closed_at.tzinfo is None:
        closed_at = closed_at.replace(tzinfo=timezone.utc)
    return max((closed_at - opened_at).total_seconds(), 0.0)
