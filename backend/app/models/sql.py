from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from sqlalchemy import Float, JSON, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SeverityEnum(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class IncidentStatusEnum(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    component_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    severity: Mapped[SeverityEnum] = mapped_column(SQLEnum(SeverityEnum), index=True, nullable=False)
    status: Mapped[IncidentStatusEnum] = mapped_column(
        SQLEnum(IncidentStatusEnum), index=True, default=IncidentStatusEnum.OPEN, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    signal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mttr_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    rca: Mapped["RCA"] = relationship(back_populates="incident", cascade="all, delete-orphan", uselist=False)
    state_transitions: Mapped[list["IncidentStateTransition"]] = relationship(back_populates="incident", cascade="all, delete-orphan")


class RCA(Base):
    __tablename__ = "rca"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), unique=True, nullable=False)
    root_cause_category: Mapped[str] = mapped_column(String(120), nullable=False)
    root_cause_summary: Mapped[str] = mapped_column(Text, nullable=False)
    fix_description: Mapped[str] = mapped_column(Text, nullable=False)
    prevention_plan: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    incident: Mapped[Incident] = relationship(back_populates="rca")

class IncidentStateTransition(Base):
    __tablename__ = "incident_state_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    new_status: Mapped[IncidentStatusEnum] = mapped_column(SQLEnum(IncidentStatusEnum), nullable=False)
    transitioned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(120), default="system", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    incident: Mapped[Incident] = relationship(back_populates="state_transitions")

class IncidentSignalLink(Base):
    __tablename__ = "incident_signal_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    signal_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    component_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IncidentMetric(Base):
    __tablename__ = "incident_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    bucket_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    tags: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
