from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "Incident Management System"
    environment: str = "development"
    api_prefix: str = "/api"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    postgres_dsn: str = "postgresql+asyncpg://ims:ims@localhost:5432/ims"
    mongo_dsn: str = "mongodb://localhost:27017"
    mongo_db_name: str = "ims"
    redis_dsn: str = "redis://localhost:6379/0"

    signal_debounce_seconds: int = 10
    rate_limit_per_minute: int = 1200
    worker_stream: str = "ims:signals"
    incident_cache_ttl_seconds: int = 300


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
