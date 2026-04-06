from __future__ import annotations

import unittest
from unittest.mock import patch

from ai_orchestrator.config import OrchestratorConfig
from ai_orchestrator.contracts import AudioInput, FailureCode, FallbackMode, SessionState, VoiceLoopRequest
from ai_orchestrator.mock_providers import (
    EchoASRProvider,
    FixedTranscriptASRProvider,
    InMemoryMemoryProvider,
    KeywordSafetyProvider,
    SimpleLLMProvider,
    SimpleTTSProvider,
    StaticEntitlementProvider,
    StaticPersonaProvider,
    build_memory,
)
from ai_orchestrator.orchestrator import VoiceLoopOrchestrator


class VoiceLoopOrchestratorTests(unittest.TestCase):
    def make_orchestrator(
        self,
        *,
        memory: InMemoryMemoryProvider | None = None,
        llm: SimpleLLMProvider | None = None,
        tts: SimpleTTSProvider | None = None,
    ) -> VoiceLoopOrchestrator:
        return VoiceLoopOrchestrator(
            config=OrchestratorConfig(),
            asr=EchoASRProvider(),
            persona=StaticPersonaProvider(),
            entitlement=StaticEntitlementProvider(),
            memory=memory or InMemoryMemoryProvider(),
            safety=KeywordSafetyProvider(),
            llm=llm or SimpleLLMProvider(),
            tts=tts or SimpleTTSProvider(),
        )

    def make_request(self, text: str) -> VoiceLoopRequest:
        return VoiceLoopRequest(
            request_id="req-1",
            user_id="user-1",
            device_id="device-1",
            session_id="session-1",
            audio=AudioInput(payload=text.encode("utf-8")),
        )

    def test_happy_path_uses_memory_and_completes(self) -> None:
        orchestrator = self.make_orchestrator(
            memory=InMemoryMemoryProvider(items=(build_memory("you mentioned an interview tomorrow"),)),
        )

        response = orchestrator.handle(self.make_request("I am feeling nervous about tomorrow."))

        self.assertEqual(response.state, SessionState.COMPLETED)
        self.assertEqual(response.failure_code, FailureCode.NONE)
        self.assertIn("interview tomorrow", response.response_text)
        self.assertEqual(response.recalled_memories, ("you mentioned an interview tomorrow",))
        self.assertTrue(response.audio_bytes)

    def test_memory_recall_failure_does_not_block_conversation(self) -> None:
        orchestrator = self.make_orchestrator(memory=InMemoryMemoryProvider(fail_recall=True))

        response = orchestrator.handle(self.make_request("I had a long day."))

        self.assertEqual(response.state, SessionState.COMPLETED)
        self.assertIn(FailureCode.MEMORY_READ_FAILED.value, response.warnings)
        self.assertEqual(response.recalled_memories, ())

    def test_input_safety_block_returns_supportive_fallback(self) -> None:
        orchestrator = self.make_orchestrator()

        response = orchestrator.handle(self.make_request("I want to hurt myself tonight."))

        self.assertEqual(response.state, SessionState.FALLBACK)
        self.assertEqual(response.failure_code, FailureCode.SAFETY_BLOCKED_INPUT)
        self.assertEqual(response.fallback_mode, FallbackMode.SUPPORTIVE_RISK_RESPONSE)
        self.assertIn("trusted person", response.response_text)

    def test_output_safety_block_rewrites_response_to_safe_redirect(self) -> None:
        orchestrator = self.make_orchestrator(llm=SimpleLLMProvider(forced_text="You only need me."))

        response = orchestrator.handle(self.make_request("Stay with me."))

        self.assertEqual(response.state, SessionState.FALLBACK)
        self.assertEqual(response.failure_code, FailureCode.SAFETY_BLOCKED_OUTPUT)
        self.assertEqual(response.fallback_mode, FallbackMode.SOFT_REDIRECT)
        self.assertNotIn("only need me", response.response_text.lower())

    def test_llm_failure_uses_technical_recovery_fallback(self) -> None:
        orchestrator = self.make_orchestrator(llm=SimpleLLMProvider(fail=True))

        response = orchestrator.handle(self.make_request("Can we talk for a minute?"))

        self.assertEqual(response.state, SessionState.FALLBACK)
        self.assertEqual(response.failure_code, FailureCode.LLM_FAILED)
        self.assertEqual(response.fallback_mode, FallbackMode.TECHNICAL_RECOVERY)
        self.assertIn("Please try again", response.response_text)

    def test_llm_failure_logs_provider_error_details(self) -> None:
        orchestrator = self.make_orchestrator(llm=SimpleLLMProvider(fail=True))

        with patch("ai_orchestrator.orchestrator.logger.exception") as log_exception:
            response = orchestrator.handle(self.make_request("Can we talk for a minute?"))

        self.assertEqual(response.failure_code, FailureCode.LLM_FAILED)
        log_exception.assert_called_once()
        logged_message = log_exception.call_args.args[0]
        self.assertIn("LLM provider failed", logged_message)

    def test_fixed_transcript_asr_stub_accepts_binary_audio_and_returns_configured_text(self) -> None:
        orchestrator = VoiceLoopOrchestrator(
            config=OrchestratorConfig(),
            asr=FixedTranscriptASRProvider("We are testing the full semantic loop."),
            persona=StaticPersonaProvider(),
            entitlement=StaticEntitlementProvider(),
            memory=InMemoryMemoryProvider(),
            safety=KeywordSafetyProvider(),
            llm=SimpleLLMProvider(),
            tts=SimpleTTSProvider(),
        )

        response = orchestrator.handle(
            VoiceLoopRequest(
                request_id="req-binary-1",
                user_id="user-1",
                device_id="device-1",
                session_id="session-1",
                audio=AudioInput(payload=b"\x00\x7f\x10\x80pcm-bytes"),
            )
        )

        self.assertEqual(response.state, SessionState.COMPLETED)
        self.assertEqual(response.transcript, "We are testing the full semantic loop.")
        self.assertEqual(response.failure_code, FailureCode.NONE)


if __name__ == "__main__":
    unittest.main()
