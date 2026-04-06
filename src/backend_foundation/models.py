"""Core backend foundation models for the MVP account/device/session scope."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class EntitlementTier(StrEnum):
    FREE = "free"
    SUBSCRIBED = "subscribed"


class BindStatus(StrEnum):
    UNBOUND = "unbound"
    BOUND = "bound"


class DeviceStatus(StrEnum):
    PAIRING_READY = "pairing_ready"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED_TO_CONNECT = "failed_to_connect"
    READY_TO_SPEAK = "ready_to_speak"
    OFFLINE = "offline"


class SessionState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    REASONING = "reasoning"
    SYNTHESIZING = "synthesizing"
    SPEAKING = "speaking"
    COMPLETED = "completed"
    FAILED = "failed"
    FALLBACK = "fallback"


class StepStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class FailureCode(StrEnum):
    AUTH_FAILED = "AUTH_FAILED"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    ASR_FAILED = "ASR_FAILED"
    CONTEXT_LOAD_FAILED = "CONTEXT_LOAD_FAILED"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_FAILED = "LLM_FAILED"
    TTS_FAILED = "TTS_FAILED"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(slots=True)
class Account:
    account_id: str
    auth_subject: str
    display_name: str | None
    default_role_id: str
    entitlement_tier: EntitlementTier
    created_at: datetime


@dataclass(slots=True)
class Device:
    device_id: str
    hardware_model: str
    firmware_version: str
    pairing_code: str
    device_status: DeviceStatus
    bind_status: BindStatus
    owner_account_id: str | None
    created_at: datetime
    last_online_at: datetime | None = None


@dataclass(slots=True)
class BindingRecord:
    binding_id: str
    account_id: str
    device_id: str
    status: BindStatus
    bound_at: datetime
    unbound_at: datetime | None = None


@dataclass(slots=True)
class EntitlementSnapshot:
    account_id: str
    tier: EntitlementTier
    features: dict[str, bool]


@dataclass(slots=True)
class SessionTransition:
    state: SessionState
    recorded_at: datetime
    notes: str | None = None


@dataclass(slots=True)
class Session:
    session_id: str
    account_id: str
    device_id: str
    role_id: str
    entitlement_tier: EntitlementTier
    state: SessionState
    asr_status: StepStatus
    llm_status: StepStatus
    tts_status: StepStatus
    safety_flag: bool
    fallback_used: bool
    continuity_recall_used: bool
    firmware_version: str
    started_at: datetime
    ended_at: datetime | None = None
    first_response_latency_ms: int | None = None
    failure_code: FailureCode | None = None
    transitions: list[SessionTransition] = field(default_factory=list)


@dataclass(slots=True)
class AdminOverview:
    total_accounts: int
    total_devices: int
    bound_devices: int
    active_sessions: int
    completed_sessions: int
    failed_sessions: int
