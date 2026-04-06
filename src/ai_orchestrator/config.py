from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class PersonaDefaults:
    default_role_id: str = "launch-companion-v0"
    default_voice_id: str = "companion-calm-v1"


@dataclass(slots=True)
class LatencyBudget:
    asr: int = 700
    context_assembly: int = 250
    llm_first_token: int = 900
    safety_total: int = 150
    tts_first_chunk: int = 500
    end_to_first_audio: int = 2500


@dataclass(slots=True)
class FallbackMessages:
    soft_redirect: str = (
        "I cannot help with that, but we can stay with what you are feeling right now."
    )
    firm_refusal: str = (
        "I cannot continue in that direction. If you want, we can talk about what you need next."
    )
    supportive_risk_response: str = (
        "I am glad you said that out loud. Please reach out to a trusted person or "
        "local emergency support right now, and move away from anything that could hurt you."
    )
    technical_recovery: str = "I had trouble responding just now. Please try again in a moment."


@dataclass(slots=True)
class OrchestratorConfig:
    max_recalled_memories: int = 2
    memory_write_enabled: bool = True
    persona: PersonaDefaults = field(default_factory=PersonaDefaults)
    latency_budget_ms: LatencyBudget = field(default_factory=LatencyBudget)
    fallback_messages: FallbackMessages = field(default_factory=FallbackMessages)

    @classmethod
    def from_json_file(cls, path: str | Path) -> "OrchestratorConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            max_recalled_memories=raw.get("max_recalled_memories", 2),
            memory_write_enabled=raw.get("memory_write_enabled", True),
            persona=PersonaDefaults(**raw.get("persona", {})),
            latency_budget_ms=LatencyBudget(**raw.get("latency_budget_ms", {})),
            fallback_messages=FallbackMessages(**raw.get("fallback_messages", {})),
        )
