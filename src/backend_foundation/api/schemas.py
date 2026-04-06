"""Pydantic schemas for the backend foundation REST API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models import BindStatus, DeviceStatus, EntitlementTier, FailureCode, SessionState, StepStatus


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)


class CreateAccountRequest(APIModel):
    auth_subject: str
    display_name: str | None = None
    default_role_id: str = "launch-companion-v0"


class RegisterDeviceRequest(APIModel):
    device_id: str
    hardware_model: str
    firmware_version: str
    pairing_code: str


class BindDeviceRequest(APIModel):
    pairing_code: str


class StartSessionRequest(APIModel):
    account_id: str
    device_id: str
    firmware_version: str
    role_id: str | None = None


class UpdateSessionRequest(APIModel):
    state: SessionState
    asr_status: StepStatus | None = None
    llm_status: StepStatus | None = None
    tts_status: StepStatus | None = None
    safety_flag: bool | None = None
    fallback_used: bool | None = None
    continuity_recall_used: bool | None = None
    first_response_latency_ms: int | None = None
    failure_code: FailureCode | None = None
    notes: str | None = None


class RunVoiceLoopRequest(APIModel):
    request_id: str
    audio_base64: str
    audio_format: str = "audio/wav"
    sample_rate_hz: int = 16000
    duration_ms: int | None = None
    locale: str = "en-US"


class AccountResponse(APIModel):
    account_id: str
    auth_subject: str
    display_name: str | None
    default_role_id: str
    entitlement_tier: EntitlementTier
    created_at: datetime


class DeviceResponse(APIModel):
    device_id: str
    hardware_model: str
    firmware_version: str
    device_status: DeviceStatus
    bind_status: BindStatus
    owner_account_id: str | None
    pairing_code: str
    last_online_at: datetime | None = None
    created_at: datetime


class BindingResponse(APIModel):
    binding_id: str
    account_id: str
    device_id: str
    status: BindStatus
    bound_at: datetime
    unbound_at: datetime | None = None


class EntitlementSnapshotResponse(APIModel):
    account_id: str
    tier: EntitlementTier
    features: dict[str, bool]


class SessionTransitionResponse(APIModel):
    state: SessionState
    recorded_at: datetime
    notes: str | None = None


class SessionResponse(APIModel):
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
    transitions: list[SessionTransitionResponse]


class VoiceLoopExecutionResponse(APIModel):
    session: SessionResponse
    transcript: str | None = None
    response_text: str
    audio_base64: str | None = None
    audio_format: str | None = None
    audio_url: str | None = None
    fallback_mode: str
    runtime_failure_code: str
    safety_tags: list[str] = Field(default_factory=list)
    recalled_memories: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AdminOverviewResponse(APIModel):
    total_accounts: int
    total_devices: int
    bound_devices: int
    active_sessions: int
    completed_sessions: int
    failed_sessions: int


class DeviceListResponse(APIModel):
    items: list[DeviceResponse]


class SessionListResponse(APIModel):
    items: list[SessionResponse]


class ErrorResponse(APIModel):
    code: str
    message: str
