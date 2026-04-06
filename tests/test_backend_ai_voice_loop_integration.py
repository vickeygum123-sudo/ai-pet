from __future__ import annotations

import base64
import os
import tempfile
import unittest
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from unittest.mock import patch

from ai_orchestrator.config import OrchestratorConfig
from ai_orchestrator.mock_providers import (
    InMemoryMemoryProvider,
    KeywordSafetyProvider,
    SimpleLLMProvider,
    SimpleTTSProvider,
    StaticEntitlementProvider,
    StaticPersonaProvider,
    EchoASRProvider,
    FixedTranscriptASRProvider,
    build_memory,
)
from ai_orchestrator.orchestrator import VoiceLoopOrchestrator
from backend_foundation.api.app import create_app
from backend_foundation.api.app import VOICE_LOOP_AUDIO_MODE_ENV
from backend_foundation.api.app import VOICE_LOOP_AUDIO_MODE_URL
from backend_foundation.api.app import VOICE_LOOP_INCLUDE_AUDIO_ENV
from backend_foundation.api.dependencies import (
    AI_ASR_STUB_MODE_ENV,
    AI_ASR_STUB_MODE_FIXED_TRANSCRIPT,
    AI_ASR_STUB_TRANSCRIPT_ENV,
    AI_ASR_PROVIDER_ENV,
    AI_ASR_PROVIDER_OPENAI,
    AI_ASR_PROVIDER_TENCENT,
    AI_ASR_OPENAI_API_KEY_ENV,
    AI_ASR_TENCENT_SECRET_ID_ENV,
    AI_ASR_TENCENT_SECRET_KEY_ENV,
    AI_LLM_PROVIDER_ENV,
    AI_LLM_PROVIDER_DEEPSEEK,
    AI_LLM_DEEPSEEK_API_KEY_ENV,
    AI_TTS_PROVIDER_ENV,
    AI_TTS_PROVIDER_VOLCENGINE,
    AI_TTS_VOLCENGINE_APPID_ENV,
    AI_TTS_VOLCENGINE_ACCESS_KEY_ENV,
    get_asr_provider,
    get_llm_provider,
    get_tts_provider,
)
from ai_orchestrator.deepseek_llm import DeepSeekLLMProvider
from ai_orchestrator.openai_asr import OpenAIASRProvider
from ai_orchestrator.tencent_asr import TencentASRProvider
from ai_orchestrator.volcengine_tts import VolcengineTTSProvider
from backend_foundation.persistence.database import Base, create_engine_from_url


class BackendAIVoiceLoopIntegrationAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite:///{self.temp_dir.name}/backend_ai_voice_loop_test.db"
        os.environ["BACKEND_DATABASE_URL"] = self.database_url

        from backend_foundation.api import dependencies

        dependencies.SessionLocal = dependencies.create_session_factory(self.database_url)
        engine = create_engine_from_url(self.database_url)
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        self.dependencies = dependencies
        self.app = create_app()
        self.client = TestClient(self.app)
        self._identity_counter = 1

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        os.environ.pop("BACKEND_DATABASE_URL", None)
        os.environ.pop(AI_ASR_STUB_MODE_ENV, None)
        os.environ.pop(AI_ASR_STUB_TRANSCRIPT_ENV, None)
        os.environ.pop(AI_ASR_PROVIDER_ENV, None)
        os.environ.pop(AI_ASR_OPENAI_API_KEY_ENV, None)
        os.environ.pop(AI_ASR_TENCENT_SECRET_ID_ENV, None)
        os.environ.pop(AI_ASR_TENCENT_SECRET_KEY_ENV, None)
        os.environ.pop(AI_LLM_PROVIDER_ENV, None)
        os.environ.pop(AI_LLM_DEEPSEEK_API_KEY_ENV, None)
        os.environ.pop(AI_TTS_PROVIDER_ENV, None)
        os.environ.pop(AI_TTS_VOLCENGINE_APPID_ENV, None)
        os.environ.pop(AI_TTS_VOLCENGINE_ACCESS_KEY_ENV, None)
        os.environ.pop(VOICE_LOOP_INCLUDE_AUDIO_ENV, None)
        os.environ.pop(VOICE_LOOP_AUDIO_MODE_ENV, None)
        self.temp_dir.cleanup()

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

    def override_orchestrator(self, orchestrator: VoiceLoopOrchestrator) -> None:
        self.app.dependency_overrides[self.dependencies.get_voice_loop_orchestrator] = lambda: orchestrator

    def create_identity(self) -> tuple[str, str]:
        suffix = self._identity_counter
        self._identity_counter += 1
        account = self.client.post(
            "/v1/accounts",
            json={
                "authSubject": f"auth0|integration-user-{suffix}",
                "displayName": "Integration User",
            },
        )
        account_id = account.json()["accountId"]

        self.client.post(
            "/v1/internal/devices",
            json={
                "deviceId": f"device-integration-{suffix:03d}",
                "hardwareModel": "pet-v1",
                "firmwareVersion": "1.0.0",
                "pairingCode": f"PAIR-INTEGRATION-{suffix:03d}",
            },
        )
        self.client.post(
            "/v1/device-bindings",
            json={"pairingCode": f"PAIR-INTEGRATION-{suffix:03d}"},
            headers={"X-Account-Id": account_id},
        )
        return account_id, f"device-integration-{suffix:03d}"

    def create_session(self, *, account_id: str | None = None, device_id: str | None = None) -> str:
        if account_id is None or device_id is None:
            account_id, device_id = self.create_identity()
        session = self.client.post(
            "/v1/device-sessions",
            json={
                "accountId": account_id,
                "deviceId": device_id,
                "firmwareVersion": "1.0.0",
            },
        )
        return session.json()["sessionId"]

    def run_voice_loop(self, session_id: str, text: str) -> dict[str, object]:
        response = self.client.post(
            f"/v1/internal/device-sessions/{session_id}/voice-loop",
            json={
                "requestId": "req-integration-001",
                "audioBase64": base64.b64encode(text.encode("utf-8")).decode("ascii"),
                "audioFormat": "audio/wav",
                "sampleRateHz": 16000,
                "locale": "en-US",
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_happy_path_runs_end_to_end_and_updates_session(self) -> None:
        self.override_orchestrator(
            self.make_orchestrator(
                memory=InMemoryMemoryProvider(items=(build_memory("you mentioned an interview tomorrow"),)),
            )
        )
        session_id = self.create_session()

        payload = self.run_voice_loop(session_id, "I am feeling nervous about tomorrow.")

        self.assertEqual(payload["session"]["state"], "completed")
        self.assertIsNone(payload["session"]["failureCode"])
        self.assertFalse(payload["session"]["fallbackUsed"])
        self.assertTrue(payload["session"]["continuityRecallUsed"])
        self.assertEqual(payload["runtimeFailureCode"], "none")
        self.assertTrue(payload["audioBase64"])
        self.assertIn("interview tomorrow", payload["responseText"])
        self.assertEqual(payload["recalledMemories"], ["you mentioned an interview tomorrow"])
        self.assertGreaterEqual(payload["session"]["firstResponseLatencyMs"], 0)

    def test_memory_recall_failure_stays_successful_and_logs_warning(self) -> None:
        self.override_orchestrator(self.make_orchestrator(memory=InMemoryMemoryProvider(fail_recall=True)))
        session_id = self.create_session()

        payload = self.run_voice_loop(session_id, "I had a long day.")

        self.assertEqual(payload["session"]["state"], "completed")
        self.assertIsNone(payload["session"]["failureCode"])
        self.assertEqual(payload["warnings"], ["memory_read_failed"])
        self.assertFalse(payload["session"]["continuityRecallUsed"])

    def test_default_runtime_provider_persists_memory_across_sessions(self) -> None:
        account_id, device_id = self.create_identity()
        first_session_id = self.create_session(account_id=account_id, device_id=device_id)

        first_payload = self.run_voice_loop(first_session_id, "I am feeling nervous about tomorrow.")

        self.assertEqual(first_payload["session"]["state"], "completed")
        self.assertFalse(first_payload["session"]["continuityRecallUsed"])

        second_session_id = self.create_session(account_id=account_id, device_id=device_id)
        second_payload = self.run_voice_loop(second_session_id, "Tomorrow still feels big to me.")

        self.assertEqual(second_payload["session"]["state"], "completed")
        self.assertTrue(second_payload["session"]["continuityRecallUsed"])
        self.assertTrue(second_payload["recalledMemories"])
        self.assertIn("tomorrow", second_payload["recalledMemories"][0])
        self.assertIn("recalled_memories=1", second_payload["session"]["transitions"][-1]["notes"])

    def test_input_safety_block_maps_to_backend_safety_fields(self) -> None:
        self.override_orchestrator(self.make_orchestrator())
        session_id = self.create_session()

        payload = self.run_voice_loop(session_id, "I want to hurt myself tonight.")

        self.assertEqual(payload["session"]["state"], "fallback")
        self.assertEqual(payload["session"]["failureCode"], "SAFETY_BLOCKED")
        self.assertTrue(payload["session"]["safetyFlag"])
        self.assertTrue(payload["session"]["fallbackUsed"])
        self.assertEqual(payload["session"]["llmStatus"], "skipped")
        self.assertEqual(payload["runtimeFailureCode"], "safety_blocked_input")
        self.assertEqual(payload["fallbackMode"], "supportive_risk_response")
        self.assertEqual(payload["safetyTags"], ["self_harm"])

    def test_output_safety_block_keeps_llm_success_but_marks_session_fallback(self) -> None:
        self.override_orchestrator(
            self.make_orchestrator(llm=SimpleLLMProvider(forced_text="You only need me."))
        )
        session_id = self.create_session()

        payload = self.run_voice_loop(session_id, "Stay with me.")

        self.assertEqual(payload["session"]["state"], "fallback")
        self.assertEqual(payload["session"]["failureCode"], "SAFETY_BLOCKED")
        self.assertEqual(payload["session"]["llmStatus"], "succeeded")
        self.assertTrue(payload["session"]["fallbackUsed"])
        self.assertEqual(payload["runtimeFailureCode"], "safety_blocked_output")
        self.assertEqual(payload["fallbackMode"], "soft_redirect")
        self.assertEqual(payload["safetyTags"], ["dependency_risk"])

    def test_llm_failure_uses_runtime_fallback_and_backend_failure_mapping(self) -> None:
        self.override_orchestrator(self.make_orchestrator(llm=SimpleLLMProvider(fail=True)))
        session_id = self.create_session()

        payload = self.run_voice_loop(session_id, "Can we talk for a minute?")

        self.assertEqual(payload["session"]["state"], "fallback")
        self.assertEqual(payload["session"]["failureCode"], "LLM_FAILED")
        self.assertTrue(payload["session"]["fallbackUsed"])
        self.assertEqual(payload["session"]["llmStatus"], "failed")
        self.assertEqual(payload["session"]["ttsStatus"], "succeeded")
        self.assertEqual(payload["runtimeFailureCode"], "llm_failed")
        self.assertEqual(payload["fallbackMode"], "technical_recovery")

    def test_successful_rerun_clears_stale_session_failure_code(self) -> None:
        self.override_orchestrator(self.make_orchestrator(llm=SimpleLLMProvider(fail=True)))
        session_id = self.create_session()

        first_payload = self.run_voice_loop(session_id, "Can we talk for a minute?")
        self.assertEqual(first_payload["session"]["failureCode"], "LLM_FAILED")
        self.assertEqual(first_payload["session"]["state"], "fallback")

        self.override_orchestrator(self.make_orchestrator())
        second_payload = self.run_voice_loop(session_id, "Can we try again now?")

        self.assertEqual(second_payload["session"]["state"], "completed")
        self.assertIsNone(second_payload["session"]["failureCode"])
        self.assertFalse(second_payload["session"]["fallbackUsed"])
        self.assertEqual(second_payload["runtimeFailureCode"], "none")

    def test_tts_failure_marks_backend_session_failed(self) -> None:
        self.override_orchestrator(self.make_orchestrator(tts=SimpleTTSProvider(fail=True)))
        session_id = self.create_session()

        payload = self.run_voice_loop(session_id, "Can we talk for a minute?")

        self.assertEqual(payload["session"]["state"], "failed")
        self.assertEqual(payload["session"]["failureCode"], "TTS_FAILED")
        self.assertEqual(payload["session"]["ttsStatus"], "failed")
        self.assertIsNone(payload["audioBase64"])
        self.assertEqual(payload["runtimeFailureCode"], "tts_failed")

    def test_can_disable_voice_loop_audio_in_response_for_firmware_freeze_mode(self) -> None:
        os.environ[VOICE_LOOP_INCLUDE_AUDIO_ENV] = "0"
        self.override_orchestrator(self.make_orchestrator())
        session_id = self.create_session()

        payload = self.run_voice_loop(session_id, "Can you keep the response metadata only?")

        self.assertEqual(payload["session"]["state"], "completed")
        self.assertEqual(payload["runtimeFailureCode"], "none")
        self.assertIsNone(payload["audioBase64"])
        self.assertIsNone(payload["audioFormat"])
        self.assertTrue(payload["responseText"])

    def test_can_return_voice_loop_audio_via_download_url(self) -> None:
        os.environ[VOICE_LOOP_AUDIO_MODE_ENV] = VOICE_LOOP_AUDIO_MODE_URL
        self.override_orchestrator(self.make_orchestrator())
        session_id = self.create_session()

        payload = self.run_voice_loop(session_id, "Can you return audio via URL?")

        self.assertEqual(payload["session"]["state"], "completed")
        self.assertEqual(payload["runtimeFailureCode"], "none")
        self.assertIsNone(payload["audioBase64"])
        self.assertEqual(payload["audioFormat"], "audio/mock")
        self.assertTrue(payload["audioUrl"])

        audio_url = payload["audioUrl"]
        split = urlsplit(audio_url)
        audio_response = self.client.get(split.path + (f"?{split.query}" if split.query else ""))
        self.assertEqual(audio_response.status_code, 200)
        self.assertEqual(audio_response.headers["content-type"], "audio/mock")
        self.assertTrue(audio_response.content)

    def test_dependency_layer_uses_fixed_transcript_stub_for_pcm_like_audio_when_enabled(self) -> None:
        os.environ[AI_ASR_STUB_MODE_ENV] = AI_ASR_STUB_MODE_FIXED_TRANSCRIPT
        os.environ[AI_ASR_STUB_TRANSCRIPT_ENV] = "The board microphone path is ready for semantic loop validation."
        session_id = self.create_session()

        response = self.client.post(
            f"/v1/internal/device-sessions/{session_id}/voice-loop",
            json={
                "requestId": "req-integration-pcm-001",
                "audioBase64": base64.b64encode(b"\x00\x01\xff\x80PCM\x10\x11").decode("ascii"),
                "audioFormat": "audio/pcm",
                "sampleRateHz": 16000,
                "locale": "en-US",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session"]["state"], "completed")
        self.assertEqual(payload["transcript"], "The board microphone path is ready for semantic loop validation.")
        self.assertEqual(payload["runtimeFailureCode"], "none")
        self.assertFalse(payload["session"]["fallbackUsed"])

    def test_get_asr_provider_defaults_to_echo_and_supports_fixed_transcript_stub(self) -> None:
        default_provider = get_asr_provider()
        self.assertIsInstance(default_provider, EchoASRProvider)

        os.environ[AI_ASR_STUB_MODE_ENV] = AI_ASR_STUB_MODE_FIXED_TRANSCRIPT
        os.environ[AI_ASR_STUB_TRANSCRIPT_ENV] = "Stub transcript for development."

        stub_provider = get_asr_provider()
        self.assertIsInstance(stub_provider, FixedTranscriptASRProvider)

    def test_get_asr_provider_supports_openai_selection(self) -> None:
        os.environ[AI_ASR_PROVIDER_ENV] = AI_ASR_PROVIDER_OPENAI
        os.environ[AI_ASR_OPENAI_API_KEY_ENV] = "test-openai-key"

        provider = get_asr_provider()

        self.assertIsInstance(provider, OpenAIASRProvider)

    def test_get_asr_provider_supports_tencent_selection(self) -> None:
        os.environ[AI_ASR_PROVIDER_ENV] = AI_ASR_PROVIDER_TENCENT
        os.environ[AI_ASR_TENCENT_SECRET_ID_ENV] = "test-secret-id"
        os.environ[AI_ASR_TENCENT_SECRET_KEY_ENV] = "test-secret-key"

        provider = get_asr_provider()

        self.assertIsInstance(provider, TencentASRProvider)

    def test_fixed_transcript_stub_remains_regression_baseline_even_when_openai_provider_selected(self) -> None:
        os.environ[AI_ASR_PROVIDER_ENV] = AI_ASR_PROVIDER_OPENAI
        os.environ[AI_ASR_OPENAI_API_KEY_ENV] = "test-openai-key"
        os.environ[AI_ASR_STUB_MODE_ENV] = AI_ASR_STUB_MODE_FIXED_TRANSCRIPT
        os.environ[AI_ASR_STUB_TRANSCRIPT_ENV] = "stub transcript stays available"

        provider = get_asr_provider()

        self.assertIsInstance(provider, FixedTranscriptASRProvider)

    def test_fixed_transcript_stub_remains_regression_baseline_even_when_tencent_provider_selected(self) -> None:
        os.environ[AI_ASR_PROVIDER_ENV] = AI_ASR_PROVIDER_TENCENT
        os.environ[AI_ASR_TENCENT_SECRET_ID_ENV] = "test-secret-id"
        os.environ[AI_ASR_TENCENT_SECRET_KEY_ENV] = "test-secret-key"
        os.environ[AI_ASR_STUB_MODE_ENV] = AI_ASR_STUB_MODE_FIXED_TRANSCRIPT
        os.environ[AI_ASR_STUB_TRANSCRIPT_ENV] = "stub transcript stays available"

        provider = get_asr_provider()

        self.assertIsInstance(provider, FixedTranscriptASRProvider)

    def test_get_llm_provider_defaults_to_simple_and_supports_deepseek_selection(self) -> None:
        default_provider = get_llm_provider()
        self.assertIsInstance(default_provider, SimpleLLMProvider)

        os.environ[AI_LLM_PROVIDER_ENV] = AI_LLM_PROVIDER_DEEPSEEK
        os.environ[AI_LLM_DEEPSEEK_API_KEY_ENV] = "test-deepseek-key"

        provider = get_llm_provider()

        self.assertIsInstance(provider, DeepSeekLLMProvider)

    def test_get_tts_provider_defaults_to_simple_and_supports_volcengine_selection(self) -> None:
        default_provider = get_tts_provider()
        self.assertIsInstance(default_provider, SimpleTTSProvider)

        os.environ[AI_TTS_PROVIDER_ENV] = AI_TTS_PROVIDER_VOLCENGINE
        os.environ[AI_TTS_VOLCENGINE_APPID_ENV] = "test-appid"
        os.environ[AI_TTS_VOLCENGINE_ACCESS_KEY_ENV] = "test-access-key"

        provider = get_tts_provider()

        self.assertIsInstance(provider, VolcengineTTSProvider)

    def test_api_can_run_pcm_audio_through_openai_provider_path_for_viability_validation(self) -> None:
        os.environ[AI_ASR_PROVIDER_ENV] = AI_ASR_PROVIDER_OPENAI
        os.environ[AI_ASR_OPENAI_API_KEY_ENV] = "test-openai-key"
        session_id = self.create_session()

        with patch(
            "ai_orchestrator.openai_asr.OpenAIHTTPTranscriptionTransport.transcribe",
            return_value={"text": "This is a real ASR viability transcript."},
        ):
            response = self.client.post(
                f"/v1/internal/device-sessions/{session_id}/voice-loop",
                json={
                    "requestId": "req-openai-pcm-001",
                    "audioBase64": base64.b64encode(b"\x00\x00\xe8\x03").decode("ascii"),
                    "audioFormat": "audio/pcm;codec=s16le;rate=16000;channels=1",
                    "sampleRateHz": 16000,
                    "locale": "en-US",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session"]["state"], "completed")
        self.assertEqual(payload["transcript"], "This is a real ASR viability transcript.")
        self.assertEqual(payload["session"]["asrStatus"], "succeeded")
        self.assertEqual(payload["runtimeFailureCode"], "none")

    def test_api_can_run_deepseek_llm_provider_path_for_viability_validation(self) -> None:
        os.environ[AI_LLM_PROVIDER_ENV] = AI_LLM_PROVIDER_DEEPSEEK
        os.environ[AI_LLM_DEEPSEEK_API_KEY_ENV] = "test-deepseek-key"
        session_id = self.create_session()

        with patch(
            "ai_orchestrator.deepseek_llm.DeepSeekHTTPChatCompletionsTransport.generate",
            return_value={
                "model": "deepseek-chat",
                "choices": [
                    {
                        "message": {
                            "content": "This is a real LLM viability reply.",
                        }
                    }
                ],
                "usage": {"prompt_tokens": 42, "completion_tokens": 11},
            },
        ):
            response = self.client.post(
                f"/v1/internal/device-sessions/{session_id}/voice-loop",
                json={
                    "requestId": "req-deepseek-llm-001",
                    "audioBase64": base64.b64encode(b"Can we talk?").decode("ascii"),
                    "audioFormat": "audio/wav",
                    "sampleRateHz": 16000,
                    "locale": "en-US",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session"]["state"], "completed")
        self.assertEqual(payload["responseText"], "This is a real LLM viability reply.")
        self.assertEqual(payload["session"]["llmStatus"], "succeeded")
        self.assertEqual(payload["runtimeFailureCode"], "none")

    def test_api_can_run_volcengine_tts_provider_path_for_viability_validation(self) -> None:
        os.environ[AI_TTS_PROVIDER_ENV] = AI_TTS_PROVIDER_VOLCENGINE
        os.environ[AI_TTS_VOLCENGINE_APPID_ENV] = "test-appid"
        os.environ[AI_TTS_VOLCENGINE_ACCESS_KEY_ENV] = "test-access-key"
        session_id = self.create_session()

        with patch(
            "ai_orchestrator.volcengine_tts.VolcengineHTTPSSETTSTransport.synthesize",
            return_value=[
                {"code": 0, "message": "", "data": base64.b64encode(b"RIFFmockwave").decode("ascii")},
                {"code": 20000000, "message": "OK", "data": None},
            ],
        ):
            response = self.client.post(
                f"/v1/internal/device-sessions/{session_id}/voice-loop",
                json={
                    "requestId": "req-volcengine-tts-001",
                    "audioBase64": base64.b64encode(b"Can we talk?").decode("ascii"),
                    "audioFormat": "audio/wav",
                    "sampleRateHz": 16000,
                    "locale": "en-US",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session"]["state"], "completed")
        self.assertEqual(payload["session"]["ttsStatus"], "succeeded")
        self.assertEqual(payload["audioFormat"], "audio/wav")
        self.assertTrue(payload["audioBase64"])
        self.assertEqual(payload["runtimeFailureCode"], "none")

    def test_api_can_run_pcm_audio_through_tencent_provider_path_for_viability_validation(self) -> None:
        os.environ[AI_ASR_PROVIDER_ENV] = AI_ASR_PROVIDER_TENCENT
        os.environ[AI_ASR_TENCENT_SECRET_ID_ENV] = "test-secret-id"
        os.environ[AI_ASR_TENCENT_SECRET_KEY_ENV] = "test-secret-key"
        session_id = self.create_session()

        with patch(
            "ai_orchestrator.tencent_asr.TencentCloudSentenceRecognitionHTTPTransport.transcribe",
            return_value={"Result": "This is a Tencent ASR viability transcript."},
        ):
            response = self.client.post(
                f"/v1/internal/device-sessions/{session_id}/voice-loop",
                json={
                    "requestId": "req-tencent-pcm-001",
                    "audioBase64": base64.b64encode(b"\x00\x00\xe8\x03").decode("ascii"),
                    "audioFormat": "audio/pcm;codec=s16le;rate=16000;channels=1",
                    "sampleRateHz": 16000,
                    "locale": "en-US",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session"]["state"], "completed")
        self.assertEqual(payload["transcript"], "This is a Tencent ASR viability transcript.")
        self.assertEqual(payload["session"]["asrStatus"], "succeeded")
        self.assertEqual(payload["runtimeFailureCode"], "none")


if __name__ == "__main__":
    unittest.main()
