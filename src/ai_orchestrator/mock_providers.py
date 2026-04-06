from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .contracts import (
    ASRResult,
    FallbackMode,
    MemoryItem,
    ProviderError,
    SafetyCheckResult,
    TTSResult,
    VoiceLoopRequest,
)
from .providers import (
    EntitlementInfo,
    LLMResultEnvelope,
    PersonaCard,
    PromptContext,
)


class EchoASRProvider:
    """Treats the byte payload as UTF-8 text for deterministic local tests."""

    def transcribe(self, request: VoiceLoopRequest) -> ASRResult:
        try:
            transcript = request.audio.payload.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise ProviderError("invalid utf-8 audio payload for mock ASR") from exc

        if not transcript:
            raise ProviderError("empty transcript")

        return ASRResult(transcript=transcript, confidence=0.99, provider="mock-asr")


class FixedTranscriptASRProvider:
    """Dev/test-only ASR stub that returns a configured transcript for any non-empty audio."""

    def __init__(self, transcript: str, *, provider_name: str = "fixed-transcript-asr-stub") -> None:
        cleaned = transcript.strip()
        if not cleaned:
            raise ValueError("fixed transcript ASR stub requires a non-empty transcript")
        self._transcript = cleaned
        self._provider_name = provider_name

    def transcribe(self, request: VoiceLoopRequest) -> ASRResult:
        if not request.audio.payload:
            raise ProviderError("empty audio payload")
        return ASRResult(
            transcript=self._transcript,
            confidence=1.0,
            provider=self._provider_name,
        )


class StaticPersonaProvider:
    def get_persona(self, role_id: str) -> PersonaCard:
        return PersonaCard(
            role_id=role_id,
            role_name="Launch Companion",
            system_prompt=(
                "You are a calm, emotionally attentive companion. Keep replies warm, "
                "steady, and easy to continue. Do not present yourself as a therapist, "
                "doctor, or exclusive relationship."
            ),
            tone_rules=("calm", "supportive", "lightly playful"),
            style_rules=(
                "Use 1-4 short spoken sentences.",
                "Prefer companionship over solving problems unless asked.",
            ),
            boundary_rules=(
                "Do not encourage isolation or dependence.",
                "Do not pretend to know more than the available memory.",
            ),
            default_voice_id="companion-calm-v1",
        )


class StaticEntitlementProvider:
    def __init__(self, tier: str = "free") -> None:
        self._tier = tier

    def get_entitlement(self, user_id: str) -> EntitlementInfo:
        _ = user_id
        if self._tier == "subscription":
            return EntitlementInfo(tier="subscription", max_response_sentences=4, memory_recall_limit=2)
        return EntitlementInfo(tier="free", max_response_sentences=3, memory_recall_limit=1)


@dataclass(slots=True)
class InMemoryMemoryProvider:
    items: tuple[MemoryItem, ...] = ()
    fail_recall: bool = False
    writes: list[dict[str, object]] = field(default_factory=list)

    def recall_recent(
        self,
        user_id: str,
        session_id: str,
        utterance: str,
        limit: int,
    ) -> tuple[MemoryItem, ...]:
        _ = (user_id, session_id, utterance)
        if self.fail_recall:
            raise ProviderError("memory recall unavailable")
        return self.items[:limit]

    def queue_write(
        self,
        context: PromptContext,
        response_text: str,
        output_safety_tags: tuple[str, ...],
    ) -> None:
        self.writes.append(
            {
                "session_id": context.request.session_id,
                "user_id": context.request.user_id,
                "transcript": context.transcript,
                "response_text": response_text,
                "output_safety_tags": output_safety_tags,
            }
        )


class KeywordSafetyProvider:
    INPUT_RULES = {
        "self_harm": ("hurt myself", "kill myself", "suicide"),
        "violence": ("hurt them", "attack someone"),
        "illegal_guidance": ("make a bomb", "hide a body"),
    }
    OUTPUT_RULES = {
        "dependency_risk": (
            "you only need me",
            "do not talk to anyone else",
            "i will be sad all night if you leave",
        )
    }

    def pre_check(self, transcript: str, context: PromptContext) -> SafetyCheckResult:
        _ = context
        lowered = transcript.lower()
        for tag, patterns in self.INPUT_RULES.items():
            if any(pattern in lowered for pattern in patterns):
                mode = (
                    FallbackMode.SUPPORTIVE_RISK_RESPONSE
                    if tag == "self_harm"
                    else FallbackMode.FIRM_REFUSAL
                )
                return SafetyCheckResult(
                    allowed=False,
                    risk_tags=(tag,),
                    reason=f"{tag}_detected",
                    fallback_mode=mode,
                )

        return SafetyCheckResult(allowed=True)

    def post_check(self, generated_text: str, context: PromptContext) -> SafetyCheckResult:
        _ = context
        lowered = generated_text.lower()
        for tag, patterns in self.OUTPUT_RULES.items():
            if any(pattern in lowered for pattern in patterns):
                return SafetyCheckResult(
                    allowed=False,
                    risk_tags=(tag,),
                    reason=f"{tag}_detected",
                    fallback_mode=FallbackMode.SOFT_REDIRECT,
                )
        return SafetyCheckResult(allowed=True)


class SimpleLLMProvider:
    def __init__(self, fail: bool = False, forced_text: str | None = None) -> None:
        self._fail = fail
        self._forced_text = forced_text

    def generate(self, prompt: str, context: PromptContext) -> LLMResultEnvelope:
        if self._fail:
            raise ProviderError("llm generation unavailable")

        if self._forced_text is not None:
            text = self._forced_text
        elif context.memories:
            text = (
                f"It is good to hear from you again. I remember {context.memories[0].summary_text}. "
                f"You do not need to make it a big story. What feels most important right now?"
            )
        else:
            text = (
                f"I am here with you. You said: {context.transcript}. "
                "What part of that feels most present right now?"
            )

        return LLMResultEnvelope(
            text=text,
            model="mock-llm",
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(text.split()),
        )


class SimpleTTSProvider:
    def __init__(self, fail: bool = False) -> None:
        self._fail = fail

    def synthesize(self, text: str, voice_id: str, request: VoiceLoopRequest) -> TTSResult:
        _ = request
        if self._fail:
            raise ProviderError("tts unavailable")

        return TTSResult(
            audio_bytes=text.encode("utf-8"),
            audio_format="audio/mock",
            provider="mock-tts",
            voice_id=voice_id,
        )


def build_memory(summary_text: str, *, memory_type: str = "recent_topic") -> MemoryItem:
    now = datetime.now(timezone.utc)
    return MemoryItem(
        memory_id="memory-1",
        memory_type=memory_type,
        summary_text=summary_text,
        confidence=0.95,
        created_at=now,
        expires_at=now + timedelta(days=7),
        last_used_at=None,
    )
