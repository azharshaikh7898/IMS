from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from motor.motor_asyncio import AsyncIOMotorDatabase


class SignalRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self._database = database

    @property
    def collection(self):
        return self._database["raw_signals"]

    async def insert_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        await self.collection.insert_one(signal)
        return signal

    async def link_signal_to_incident(self, signal_id: str, incident_id: str) -> None:
        await self.collection.update_one({"signal_id": signal_id}, {"$set": {"incident_id": incident_id, "linked_at": datetime.now(timezone.utc)}})

    async def list_signals_for_incident(self, incident_id: str, limit: int = 100) -> list[dict[str, Any]]:
        cursor = self.collection.find({"incident_id": incident_id}).sort("occurred_at", -1).limit(limit)
        return [doc async for doc in cursor]
