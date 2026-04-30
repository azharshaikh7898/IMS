from datetime import datetime, timezone
from app.models.schemas import IncidentStatus, RCARequest
from app.services.workflow import IncidentContext, has_valid_rca, validate_transition
import pytest


def test_rca_validation_requires_text():
    rca = RCARequest(
        root_cause_category="Database",
        root_cause_summary="Primary database exhausted connections",
        fix_description="Raised pool size and optimized query",
        prevention_plan="Add pool monitoring and alerts",
        occurred_at=datetime.now(timezone.utc),
        detected_at=datetime.now(timezone.utc),
    )
    assert has_valid_rca(rca)


def test_close_without_rca_is_blocked():
    context = IncidentContext(status=IncidentStatus.RESOLVED)
    with pytest.raises(ValueError):
        validate_transition(context, IncidentStatus.CLOSED)
