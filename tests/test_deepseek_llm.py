from __future__ import annotations

import unittest

from ai_orchestrator.contracts import AudioInput, VoiceLoopRequest
from ai_orchestrator.deepseek_llm import DeepSeekLLMProvider, extract_message_text
from ai_orchestrator.mock_providers import StaticEntitlementProvider, StaticPersonaProvider
from ai_orchestrator.providers import PromptContext


class RecordingTransport:
    def __init__(self, response: dict[str, object] | None = None) -> None:
        self.response = response or {
            "model": "deepseek-chat",
            "choices": [{"message": {"content": "I am here with you."}}],
            "usage": {"prompt_tokens": 21, "completion_tokens": 8},
        }
        self.calls: list[dict[str, object]] = []

    def generate(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return self.response


class DeepSeekLLMProviderTests(unittest.TestCase):
    def make_context(self) -> PromptContext:
        request = VoiceLoopRequest(
            request_id="req-1",
            user_id="user-1",
            device_id="device-1",
            session_id="session-1",
            audio=AudioInput(payload=b"test"),
        )
        return PromptContext(
            request=request,
            transcript="I had a hard day.",
            persona=StaticPersonaProvider().get_persona("launch-companion-v0"),
            entitlement=StaticEntitlementProvider().get_entitlement("user-1"),
            memories=(),
        )

    def test_provider_returns_text_and_usage(self) -> None:
        transport = RecordingTransport()
        provider = DeepSeekLLMProvider(transport=transport, max_tokens=180)

        result = provider.generate("Prompt text", self.make_context())

        self.assertEqual(result.text, "I am here with you.")
        self.assertEqual(result.model, "deepseek-chat")
        self.assertEqual(result.prompt_tokens, 21)
        self.assertEqual(result.completion_tokens, 8)
        self.assertEqual(transport.calls[0]["max_tokens"], 180)
        self.assertEqual(transport.calls[0]["messages"][1]["content"], "Prompt text")

    def test_provider_accepts_array_content(self) -> None:
        provider = DeepSeekLLMProvider(
            transport=RecordingTransport(
                response={
                    "choices": [
                        {"message": {"content": [{"type": "text", "text": "Soft reply"}]}},
                    ]
                }
            )
        )

        result = provider.generate("Prompt text", self.make_context())

        self.assertEqual(result.text, "Soft reply")

    def test_provider_rejects_empty_text(self) -> None:
        provider = DeepSeekLLMProvider(
            transport=RecordingTransport(response={"choices": [{"message": {"content": "   "}}]})
        )

        with self.assertRaisesRegex(RuntimeError, "empty text"):
            provider.generate("Prompt text", self.make_context())

    def test_extract_message_text_handles_missing_choices(self) -> None:
        self.assertEqual(extract_message_text({}), "")


if __name__ == "__main__":
    unittest.main()
