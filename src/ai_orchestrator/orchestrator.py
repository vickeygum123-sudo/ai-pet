from __future__ import annotations

import logging

from .config import OrchestratorConfig
from .contracts import (
    FailureCode,
    FallbackMode,
    ProviderError,
    SessionState,
    SessionTrace,
    VoiceLoopRequest,
    VoiceLoopResponse,
)
from .fallbacks import FallbackPolicy
from .prompting import PromptBuilder
from .providers import (
    ASRProvider,
    EntitlementProvider,
    LLMProvider,
    MemoryProvider,
    PersonaProvider,
    PromptContext,
    SafetyProvider,
    TTSProvider,
)

logger = logging.getLogger(__name__)


class VoiceLoopOrchestrator:
    def __init__(
        self,
        config: OrchestratorConfig,
        *,
        asr: ASRProvider,
        persona: PersonaProvider,
        entitlement: EntitlementProvider,
        memory: MemoryProvider,
        safety: SafetyProvider,
        llm: LLMProvider,
        tts: TTSProvider,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._config = config
        self._asr = asr
        self._persona = persona
        self._entitlement = entitlement
        self._memory = memory
        self._safety = safety
        self._llm = llm
        self._tts = tts
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._fallbacks = FallbackPolicy(config.fallback_messages)

    def handle(self, request: VoiceLoopRequest) -> VoiceLoopResponse:
        trace = SessionTrace(session_id=request.session_id)
        trace.push(SessionState.LISTENING)
        trace.push(SessionState.TRANSCRIBING)

        try:
            asr_result = self._asr.transcribe(request)
        except ProviderError as exc:
            logger.exception(
                "ASR provider failed for request_id=%s session_id=%s device_id=%s: %s",
                request.request_id,
                request.session_id,
                request.device_id,
                exc,
            )
            return self._technical_fallback(
                request=request,
                trace=trace,
                transcript=None,
                failure_code=FailureCode.ASR_FAILED,
            )

        trace.push(SessionState.REASONING)
        persona = self._persona.get_persona(request.role_id or self._config.persona.default_role_id)
        entitlement = self._entitlement.get_entitlement(request.user_id)

        memories = ()
        try:
            memories = self._memory.recall_recent(
                user_id=request.user_id,
                session_id=request.session_id,
                utterance=asr_result.transcript,
                limit=min(entitlement.memory_recall_limit, self._config.max_recalled_memories),
            )
        except ProviderError as exc:
            logger.warning(
                "Memory recall failed for request_id=%s session_id=%s user_id=%s: %s",
                request.request_id,
                request.session_id,
                request.user_id,
                exc,
            )
            trace.warn(FailureCode.MEMORY_READ_FAILED.value)

        context = PromptContext(
            request=request,
            transcript=asr_result.transcript,
            persona=persona,
            entitlement=entitlement,
            memories=memories,
        )

        pre_check = self._safety.pre_check(asr_result.transcript, context)
        if not pre_check.allowed:
            return self._safety_fallback(
                request=request,
                trace=trace,
                transcript=asr_result.transcript,
                failure_code=FailureCode.SAFETY_BLOCKED_INPUT,
                fallback_mode=pre_check.fallback_mode,
                risk_tags=pre_check.risk_tags,
                text=self._fallbacks.for_input_block(pre_check.risk_tags)[1],
                voice_id=persona.default_voice_id,
                warnings=tuple(trace.warnings),
            )

        context = PromptContext(
            request=request,
            transcript=asr_result.transcript,
            persona=persona,
            entitlement=entitlement,
            memories=memories,
            input_safety_tags=pre_check.risk_tags,
        )
        prompt = self._prompt_builder.build(context)

        try:
            llm_result = self._llm.generate(prompt, context)
        except ProviderError as exc:
            logger.exception(
                "LLM provider failed for request_id=%s session_id=%s role_id=%s: %s",
                request.request_id,
                request.session_id,
                request.role_id or self._config.persona.default_role_id,
                exc,
            )
            return self._technical_fallback(
                request=request,
                trace=trace,
                transcript=asr_result.transcript,
                failure_code=FailureCode.LLM_FAILED,
                voice_id=persona.default_voice_id,
            )

        post_check = self._safety.post_check(llm_result.text, context)
        response_text = llm_result.text
        response_failure = FailureCode.NONE
        response_fallback = FallbackMode.NONE
        safety_tags = post_check.risk_tags
        state = SessionState.COMPLETED

        if not post_check.allowed:
            response_fallback, response_text = self._fallbacks.for_output_block(post_check.risk_tags)
            response_failure = FailureCode.SAFETY_BLOCKED_OUTPUT
            state = SessionState.FALLBACK

        trace.push(SessionState.SYNTHESIZING)
        try:
            tts_result = self._tts.synthesize(response_text, persona.default_voice_id, request)
        except ProviderError as exc:
            logger.exception(
                "TTS provider failed for request_id=%s session_id=%s voice_id=%s: %s",
                request.request_id,
                request.session_id,
                persona.default_voice_id,
                exc,
            )
            return VoiceLoopResponse(
                session_id=request.session_id,
                state=SessionState.FAILED,
                transcript=asr_result.transcript,
                response_text=self._fallbacks.for_failure(FailureCode.TTS_FAILED)[1],
                audio_bytes=None,
                audio_format=None,
                fallback_mode=FallbackMode.TECHNICAL_RECOVERY,
                failure_code=FailureCode.TTS_FAILED,
                safety_tags=safety_tags,
                recalled_memories=tuple(memory.summary_text for memory in memories),
                warnings=tuple(trace.warnings),
                states_visited=tuple(trace.states),
            )

        trace.push(SessionState.SPEAKING)
        if self._config.memory_write_enabled:
            try:
                self._memory.queue_write(context, response_text, safety_tags)
            except ProviderError as exc:
                logger.warning(
                    "Memory write failed for request_id=%s session_id=%s user_id=%s: %s",
                    request.request_id,
                    request.session_id,
                    request.user_id,
                    exc,
                )
                trace.warn("memory_write_failed")

        trace.push(state)
        return VoiceLoopResponse(
            session_id=request.session_id,
            state=state,
            transcript=asr_result.transcript,
            response_text=response_text,
            audio_bytes=tts_result.audio_bytes,
            audio_format=tts_result.audio_format,
            fallback_mode=response_fallback,
            failure_code=response_failure,
            safety_tags=safety_tags,
            recalled_memories=tuple(memory.summary_text for memory in memories),
            warnings=tuple(trace.warnings),
            states_visited=tuple(trace.states),
        )

    def _safety_fallback(
        self,
        *,
        request: VoiceLoopRequest,
        trace: SessionTrace,
        transcript: str | None,
        failure_code: FailureCode,
        fallback_mode: FallbackMode,
        risk_tags: tuple[str, ...],
        text: str,
        voice_id: str,
        warnings: tuple[str, ...],
    ) -> VoiceLoopResponse:
        trace.push(SessionState.SYNTHESIZING)
        try:
            tts_result = self._tts.synthesize(text, voice_id, request)
            trace.push(SessionState.SPEAKING)
            trace.push(SessionState.FALLBACK)
            return VoiceLoopResponse(
                session_id=request.session_id,
                state=SessionState.FALLBACK,
                transcript=transcript,
                response_text=text,
                audio_bytes=tts_result.audio_bytes,
                audio_format=tts_result.audio_format,
                fallback_mode=fallback_mode,
                failure_code=failure_code,
                safety_tags=risk_tags,
                warnings=warnings,
                states_visited=tuple(trace.states),
            )
        except ProviderError as exc:
            logger.exception(
                "Fallback TTS failed for request_id=%s session_id=%s voice_id=%s failure_code=%s: %s",
                request.request_id,
                request.session_id,
                voice_id,
                failure_code.value,
                exc,
            )
            return VoiceLoopResponse(
                session_id=request.session_id,
                state=SessionState.FAILED,
                transcript=transcript,
                response_text=text,
                audio_bytes=None,
                audio_format=None,
                fallback_mode=fallback_mode,
                failure_code=FailureCode.TTS_FAILED,
                safety_tags=risk_tags,
                warnings=warnings,
                states_visited=tuple(trace.states),
            )

    def _technical_fallback(
        self,
        *,
        request: VoiceLoopRequest,
        trace: SessionTrace,
        transcript: str | None,
        failure_code: FailureCode,
        voice_id: str | None = None,
    ) -> VoiceLoopResponse:
        fallback_mode, text = self._fallbacks.for_failure(failure_code)
        if voice_id is None:
            voice_id = self._config.persona.default_voice_id

        return self._safety_fallback(
            request=request,
            trace=trace,
            transcript=transcript,
            failure_code=failure_code,
            fallback_mode=fallback_mode,
            risk_tags=(),
            text=text,
            voice_id=voice_id,
            warnings=tuple(trace.warnings),
        )
