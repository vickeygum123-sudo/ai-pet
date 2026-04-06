from __future__ import annotations

from .providers import PromptContext


class PromptBuilder:
    """Composes a narrow MVP prompt around persona, memory, safety, and user text."""

    def build(self, context: PromptContext) -> str:
        memory_lines = [
            f"- {memory.summary_text} (confidence={memory.confidence:.2f})"
            for memory in context.memories
        ]
        if not memory_lines:
            memory_lines = ["- none"]

        tone_lines = [f"- {rule}" for rule in context.persona.tone_rules]
        style_lines = [f"- {rule}" for rule in context.persona.style_rules]
        boundary_lines = [f"- {rule}" for rule in context.persona.boundary_rules]

        safety_tags = ", ".join(context.input_safety_tags) if context.input_safety_tags else "none"

        return "\n".join(
            [
                f"Role: {context.persona.role_name}",
                "Role instructions:",
                context.persona.system_prompt,
                "Tone rules:",
                *tone_lines,
                "Style rules:",
                *style_lines,
                "Boundary rules:",
                *boundary_lines,
                f"Entitlement tier: {context.entitlement.tier}",
                f"Max response sentences: {context.entitlement.max_response_sentences}",
                f"Safety input tags: {safety_tags}",
                "Recent continuity memory:",
                *memory_lines,
                "Response requirements:",
                "- Keep the reply concise and spoken, not essay-like.",
                "- Ask at most one gentle follow-up question.",
                "- If memory is uncertain, use soft recall phrasing.",
                f"User utterance: {context.transcript}",
            ]
        )
