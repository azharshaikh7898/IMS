from __future__ import annotations

from dataclasses import dataclass
from app.core.config import get_settings
from app.db import DatabaseBundle
from app.repositories.mongo_repo import SignalRepository
from app.repositories.redis_repo import CacheRepository
from app.repositories.sql_repo import IncidentRepository
from app.services.debouncer import DebouncerService
from app.services.incident_service import IncidentService
from app.services.insights import RCAInsightService
from app.services.rate_limiter import RedisRateLimiter
from app.services.realtime import RealtimeHub


@dataclass(slots=True)
class ServiceContainer:
    settings: object
    incidents: IncidentRepository
    signals: SignalRepository
    cache: CacheRepository
    realtime: RealtimeHub
    limiter: RedisRateLimiter
    debouncer: DebouncerService
    incident_service: IncidentService
    insights: RCAInsightService


def build_container(bundle: DatabaseBundle) -> ServiceContainer:
    settings = get_settings()
    incidents = IncidentRepository(bundle.session_factory)
    signals = SignalRepository(bundle.mongo_client[settings.mongo_db_name])
    cache = CacheRepository(bundle.redis)
    realtime = RealtimeHub(bundle.redis)
    limiter = RedisRateLimiter(cache, settings.rate_limit_per_minute)
    debouncer = DebouncerService(incidents, signals, cache, realtime, settings.signal_debounce_seconds)
    incident_service = IncidentService(incidents, signals, cache, realtime)
    insights = RCAInsightService()
    return ServiceContainer(settings, incidents, signals, cache, realtime, limiter, debouncer, incident_service, insights)
