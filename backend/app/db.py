from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.models.sql import Base


@dataclass(slots=True)
class DatabaseBundle:
    settings: Settings
    engine: Any
    session_factory: async_sessionmaker[AsyncSession]
    mongo_client: AsyncIOMotorClient
    redis: Redis


async def create_database_bundle(settings: Settings) -> DatabaseBundle:
    engine = create_async_engine(settings.postgres_dsn, pool_pre_ping=True, pool_size=10, max_overflow=20)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    mongo_client = AsyncIOMotorClient(settings.mongo_dsn)
    redis = Redis.from_url(settings.redis_dsn, decode_responses=True)
    return DatabaseBundle(settings=settings, engine=engine, session_factory=session_factory, mongo_client=mongo_client, redis=redis)


async def init_db_schema(engine, retries: int = 10, delay: float = 1.0) -> None:
    for attempt in range(retries):
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            return
        except Exception as e:
            if attempt < retries - 1:
                print(f"Database connection attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                raise


@asynccontextmanager
async def lifespan_database(settings: Settings) -> AsyncIterator[DatabaseBundle]:
    bundle = await create_database_bundle(settings)
    await init_db_schema(bundle.engine)
    try:
        yield bundle
    finally:
        await bundle.redis.aclose()
        bundle.mongo_client.close()
        await bundle.engine.dispose()
