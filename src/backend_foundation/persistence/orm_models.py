"""SQLAlchemy ORM models for the backend foundation."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..models import BindStatus, DeviceStatus, EntitlementTier, FailureCode, SessionState, StepStatus
from .database import Base


class AccountORM(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    auth_subject: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_role_id: Mapped[str] = mapped_column(String(128), nullable=False)
    entitlement_tier: Mapped[str] = mapped_column(String(32), nullable=False, default=EntitlementTier.FREE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeviceORM(Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hardware_model: Mapped[str] = mapped_column(String(128), nullable=False)
    firmware_version: Mapped[str] = mapped_column(String(64), nullable=False)
    pairing_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    device_status: Mapped[str] = mapped_column(String(32), nullable=False, default=DeviceStatus.PAIRING_READY.value)
    bind_status: Mapped[str] = mapped_column(String(32), nullable=False, default=BindStatus.UNBOUND.value)
    owner_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.account_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_online_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bindings: Mapped[list["BindingRecordORM"]] = relationship(back_populates="device")
    sessions: Mapped[list["SessionORM"]] = relationship(back_populates="device")


class BindingRecordORM(Base):
    __tablename__ = "device_bindings"

    binding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"), nullable=False)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=BindStatus.BOUND.value)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped[DeviceORM] = relationship(back_populates="bindings")


class SessionORM(Base):
    __tablename__ = "device_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"), nullable=False)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    role_id: Mapped[str] = mapped_column(String(128), nullable=False)
    entitlement_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default=SessionState.IDLE.value)
    asr_status: Mapped[str] = mapped_column(String(32), nullable=False, default=StepStatus.PENDING.value)
    llm_status: Mapped[str] = mapped_column(String(32), nullable=False, default=StepStatus.PENDING.value)
    tts_status: Mapped[str] = mapped_column(String(32), nullable=False, default=StepStatus.PENDING.value)
    safety_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    continuity_recall_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_response_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    firmware_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped[DeviceORM] = relationship(back_populates="sessions")
    transitions: Mapped[list["SessionTransitionORM"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionTransitionORM.recorded_at",
    )


class SessionTransitionORM(Base):
    __tablename__ = "session_transitions"

    transition_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("device_sessions.session_id"), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[SessionORM] = relationship(back_populates="transitions")


class ContinuityMemoryORM(Base):
    __tablename__ = "continuity_memories"

    memory_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"), nullable=False)
    source_session_id: Mapped[str] = mapped_column(ForeignKey("device_sessions.session_id"), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
