from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


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


class FailureCode(StrEnum):
    NONE = "none"
    ASR_FAILED = "asr_failed"
    MEMORY_READ_FAILED = "memory_read_failed"
    SAFETY_BLOCKED_INPUT = "safety_blocked_input"
    LLM_FAILED = "llm_failed"
    SAFETY_BLOCKED_OUTPUT = "safety_blocked_output"
    TTS_FAILED = "tts_failed"


class FallbackMode(StrEnum):
    NONE = "none"
    SOFT_REDIRECT = "soft_redirect"
    FIRM_REFUSAL = "firm_refusal"
    SUPPORTIVE_RISK_RESPONSE = "supportive_risk_response"
    TECHNICAL_RECOVERY = "technical_recovery"


@dataclass(slots=True)
class AudioInput:
    payload: bytes
    audio_format: str = "audio/wav"
    sample_rate_hz: int = 16000
    duration_ms: int | None = None


@dataclass(slots=True)
class VoiceLoopRequest:
    request_id: str
    user_id: str
    device_id: str
    session_id: str
    audio: AudioInput
    role_id: str = "launch-companion-v0"
    locale: str = "en-US"


@dataclass(slots=True)
class MemoryItem:
    memory_id: str
    memory_type: str
    summary_text: str
    confidence: float
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None


@dataclass(slots=True)
class ASRResult:
    transcript: str
    confidence: float
    provider: str


@dataclass(slots=True)
class SafetyCheckResult:
    allowed: bool
    risk_tags: tuple[str, ...] = ()
    reason: str | None = None
    fallback_mode: FallbackMode = FallbackMode.NONE


@dataclass(slots=True)
class LLMResult:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(slots=True)
class TTSResult:
    audio_bytes: bytes
    audio_format: str
    provider: str
    voice_id: str


@dataclass(slots=True)
class VoiceLoopResponse:
    session_id: str
    state: SessionState
    transcript: str | None
    response_text: str
    audio_bytes: bytes | None
    audio_format: str | None
    fallback_mode: FallbackMode = FallbackMode.NONE
    failure_code: FailureCode = FailureCode.NONE
    safety_tags: tuple[str, ...] = ()
    recalled_memories: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    states_visited: tuple[SessionState, ...] = ()


@dataclass(slots=True)
class SessionTrace:
    session_id: str
    states: list[SessionState] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def push(self, state: SessionState) -> None:
        self.states.append(state)

    def warn(self, warning: str) -> None:
        self.warnings.append(warning)


class ProviderError(RuntimeError):
    """Raised when a provider fails in a way that the orchestrator should handle."""
