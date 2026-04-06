"""Thin backend-to-AI translator and integration service for MVP voice loop."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from ai_orchestrator.contracts import (
    AudioInput,
    FailureCode as AIFailureCode,
    FallbackMode,
    SessionState as AISessionState,
    VoiceLoopRequest,
    VoiceLoopResponse,
)
from ai_orchestrator.orchestrator import VoiceLoopOrchestrator

from .application import RepositoryBackedBackendFoundationService
from .models import FailureCode as BackendFailureCode
from .models import Session, SessionState as BackendSessionState, StepStatus


@dataclass(slots=True)
class RunVoiceLoopCommand:
    request_id: str
    audio_bytes: bytes
    audio_format: str = "audio/wav"
    sample_rate_hz: int = 16000
    duration_ms: int | None = None
    locale: str = "en-US"


@dataclass(slots=True)
class VoiceLoopExecutionResult:
    session: Session
    ai_response: VoiceLoopResponse


class BackendVoiceLoopIntegrationService:
    """Runs the orchestrator and translates runtime results into backend session updates."""

    def __init__(
        self,
        *,
        backend_service: RepositoryBackedBackendFoundationService,
        orchestrator: VoiceLoopOrchestrator,
    ) -> None:
        self._backend_service = backend_service
        self._orchestrator = orchestrator

    def run(self, session_id: str, command: RunVoiceLoopCommand) -> VoiceLoopExecutionResult:
        session = self._backend_service.get_admin_session_detail(session_id)
        request = self._build_request(session, command)

        started_at = perf_counter()
        ai_response = self._orchestrator.handle(request)
        first_response_latency_ms = max(int((perf_counter() - started_at) * 1000), 0)

        backend_failure_code = map_ai_failure_code(ai_response.failure_code)
        updated_session = self._backend_service.update_session(
            session_id=session_id,
            state=BackendSessionState(ai_response.state.value),
            asr_status=map_asr_status(ai_response),
            llm_status=map_llm_status(ai_response),
            tts_status=map_tts_status(ai_response),
            safety_flag=bool(ai_response.safety_tags) or backend_failure_code is BackendFailureCode.SAFETY_BLOCKED,
            fallback_used=ai_response.fallback_mode is not FallbackMode.NONE,
            continuity_recall_used=bool(ai_response.recalled_memories),
            first_response_latency_ms=first_response_latency_ms,
            failure_code=backend_failure_code,
            notes=build_session_notes(ai_response),
        )
        return VoiceLoopExecutionResult(session=updated_session, ai_response=ai_response)

    @staticmethod
    def _build_request(session: Session, command: RunVoiceLoopCommand) -> VoiceLoopRequest:
        return VoiceLoopRequest(
            request_id=command.request_id,
            user_id=session.account_id,
            device_id=session.device_id,
            session_id=session.session_id,
            audio=AudioInput(
                payload=command.audio_bytes,
                audio_format=command.audio_format,
                sample_rate_hz=command.sample_rate_hz,
                duration_ms=command.duration_ms,
            ),
            role_id=session.role_id,
            locale=command.locale,
        )


def map_ai_failure_code(failure_code: AIFailureCode) -> BackendFailureCode | None:
    return {
        AIFailureCode.NONE: None,
        AIFailureCode.ASR_FAILED: BackendFailureCode.ASR_FAILED,
        AIFailureCode.MEMORY_READ_FAILED: None,
        AIFailureCode.SAFETY_BLOCKED_INPUT: BackendFailureCode.SAFETY_BLOCKED,
        AIFailureCode.LLM_FAILED: BackendFailureCode.LLM_FAILED,
        AIFailureCode.SAFETY_BLOCKED_OUTPUT: BackendFailureCode.SAFETY_BLOCKED,
        AIFailureCode.TTS_FAILED: BackendFailureCode.TTS_FAILED,
    }[failure_code]


def map_asr_status(response: VoiceLoopResponse) -> StepStatus:
    if response.failure_code is AIFailureCode.ASR_FAILED:
        return StepStatus.FAILED
    if response.transcript:
        return StepStatus.SUCCEEDED
    return StepStatus.SKIPPED


def map_llm_status(response: VoiceLoopResponse) -> StepStatus:
    if response.failure_code is AIFailureCode.LLM_FAILED:
        return StepStatus.FAILED
    if response.failure_code in {AIFailureCode.ASR_FAILED, AIFailureCode.SAFETY_BLOCKED_INPUT}:
        return StepStatus.SKIPPED
    return StepStatus.SUCCEEDED


def map_tts_status(response: VoiceLoopResponse) -> StepStatus:
    if response.failure_code is AIFailureCode.TTS_FAILED or response.audio_bytes is None:
        return StepStatus.FAILED
    return StepStatus.SUCCEEDED


def build_session_notes(response: VoiceLoopResponse) -> str | None:
    parts: list[str] = []
    if response.safety_tags:
        parts.append(f"safety_tags={','.join(response.safety_tags)}")
    if response.recalled_memories:
        parts.append(f"recalled_memories={len(response.recalled_memories)}")
    if response.warnings:
        parts.append(f"warnings={','.join(response.warnings)}")
    if response.states_visited:
        parts.append(f"ai_states={','.join(state.value for state in response.states_visited)}")
    return "; ".join(parts) if parts else None
