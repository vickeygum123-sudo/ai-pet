from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import ASRResult, MemoryItem, SafetyCheckResult, TTSResult, VoiceLoopRequest


@dataclass(slots=True)
class PersonaCard:
    role_id: str
    role_name: str
    system_prompt: str
    tone_rules: tuple[str, ...]
    style_rules: tuple[str, ...]
    boundary_rules: tuple[str, ...]
    default_voice_id: str


@dataclass(slots=True)
class EntitlementInfo:
    tier: str
    max_response_sentences: int = 4
    memory_recall_limit: int = 2


@dataclass(slots=True)
class PromptContext:
    request: VoiceLoopRequest
    transcript: str
    persona: PersonaCard
    entitlement: EntitlementInfo
    memories: tuple[MemoryItem, ...]
    input_safety_tags: tuple[str, ...] = ()


@dataclass(slots=True)
class LLMResultEnvelope:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ASRProvider(Protocol):
    def transcribe(self, request: VoiceLoopRequest) -> ASRResult:
        ...


class PersonaProvider(Protocol):
    def get_persona(self, role_id: str) -> PersonaCard:
        ...


class EntitlementProvider(Protocol):
    def get_entitlement(self, user_id: str) -> EntitlementInfo:
        ...


class MemoryProvider(Protocol):
    def recall_recent(
        self,
        user_id: str,
        session_id: str,
        utterance: str,
        limit: int,
    ) -> tuple[MemoryItem, ...]:
        ...

    def queue_write(
        self,
        context: PromptContext,
        response_text: str,
        output_safety_tags: tuple[str, ...],
    ) -> None:
        ...


class SafetyProvider(Protocol):
    def pre_check(self, transcript: str, context: PromptContext) -> SafetyCheckResult:
        ...

    def post_check(self, generated_text: str, context: PromptContext) -> SafetyCheckResult:
        ...


class LLMProvider(Protocol):
    def generate(self, prompt: str, context: PromptContext) -> LLMResultEnvelope:
        ...


class TTSProvider(Protocol):
    def synthesize(self, text: str, voice_id: str, request: VoiceLoopRequest) -> TTSResult:
        ...
