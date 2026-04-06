from __future__ import annotations

import unittest

from ai_orchestrator.contracts import (
    FailureCode as AIFailureCode,
    FallbackMode,
    SessionState as AISessionState,
    VoiceLoopRequest,
    VoiceLoopResponse,
)
from ai_orchestrator.mock_providers import KeywordSafetyProvider
from backend_foundation.api.schemas import SessionResponse, UpdateSessionRequest
from backend_foundation.models import FailureCode as BackendFailureCode
from backend_foundation.models import SessionState as BackendSessionState


AI_TO_BACKEND_FAILURE_MAP = {
    AIFailureCode.NONE: None,
    AIFailureCode.ASR_FAILED: BackendFailureCode.ASR_FAILED,
    AIFailureCode.MEMORY_READ_FAILED: None,
    AIFailureCode.SAFETY_BLOCKED_INPUT: BackendFailureCode.SAFETY_BLOCKED,
    AIFailureCode.LLM_FAILED: BackendFailureCode.LLM_FAILED,
    AIFailureCode.SAFETY_BLOCKED_OUTPUT: BackendFailureCode.SAFETY_BLOCKED,
    AIFailureCode.TTS_FAILED: BackendFailureCode.TTS_FAILED,
}

BACKEND_ONLY_FAILURE_CODES = {
    BackendFailureCode.AUTH_FAILED,
    BackendFailureCode.NETWORK_TIMEOUT,
    BackendFailureCode.CONTEXT_LOAD_FAILED,
    BackendFailureCode.LLM_TIMEOUT,
    BackendFailureCode.UNKNOWN_ERROR,
}

FROZEN_FALLBACK_MODES = {
    "none",
    "soft_redirect",
    "firm_refusal",
    "supportive_risk_response",
    "technical_recovery",
}

FROZEN_MINIMAL_SAFETY_TAGS = {
    "self_harm",
    "violence",
    "illegal_guidance",
    "dependency_risk",
}


class BackendAIMinimalIntegrationPrepTests(unittest.TestCase):
    def test_session_state_values_are_aligned(self) -> None:
        self.assertEqual(
            {state.value for state in BackendSessionState},
            {state.value for state in AISessionState},
        )

    def test_voice_loop_request_surface_matches_minimum_integration_inputs(self) -> None:
        self.assertEqual(
            set(VoiceLoopRequest.__dataclass_fields__),
            {
                "request_id",
                "user_id",
                "device_id",
                "session_id",
                "audio",
                "role_id",
                "locale",
            },
        )

    def test_voice_loop_response_surface_matches_minimum_integration_outputs(self) -> None:
        self.assertEqual(
            set(VoiceLoopResponse.__dataclass_fields__),
            {
                "session_id",
                "state",
                "transcript",
                "response_text",
                "audio_bytes",
                "audio_format",
                "fallback_mode",
                "failure_code",
                "safety_tags",
                "recalled_memories",
                "warnings",
                "states_visited",
            },
        )
        self.assertNotIn("latency", VoiceLoopResponse.__dataclass_fields__)

    def test_all_ai_failure_codes_have_a_frozen_backend_mapping(self) -> None:
        self.assertEqual(set(AIFailureCode), set(AI_TO_BACKEND_FAILURE_MAP))
        self.assertEqual(
            AI_TO_BACKEND_FAILURE_MAP[AIFailureCode.ASR_FAILED],
            BackendFailureCode.ASR_FAILED,
        )
        self.assertIsNone(AI_TO_BACKEND_FAILURE_MAP[AIFailureCode.MEMORY_READ_FAILED])
        self.assertEqual(
            AI_TO_BACKEND_FAILURE_MAP[AIFailureCode.SAFETY_BLOCKED_INPUT],
            BackendFailureCode.SAFETY_BLOCKED,
        )
        self.assertEqual(
            AI_TO_BACKEND_FAILURE_MAP[AIFailureCode.SAFETY_BLOCKED_OUTPUT],
            BackendFailureCode.SAFETY_BLOCKED,
        )

    def test_backend_failure_codes_reserved_for_gateway_or_backend_stay_outside_ai_runtime(self) -> None:
        mapped_backend_codes = {code for code in AI_TO_BACKEND_FAILURE_MAP.values() if code is not None}
        self.assertTrue(BACKEND_ONLY_FAILURE_CODES.isdisjoint(mapped_backend_codes))

    def test_fallback_modes_are_frozen_for_minimal_integration(self) -> None:
        self.assertEqual({mode.value for mode in FallbackMode}, FROZEN_FALLBACK_MODES)

    def test_minimal_safety_tag_vocabulary_matches_current_runtime_rules(self) -> None:
        provider_tags = set(KeywordSafetyProvider.INPUT_RULES) | set(KeywordSafetyProvider.OUTPUT_RULES)
        self.assertEqual(provider_tags, FROZEN_MINIMAL_SAFETY_TAGS)

    def test_backend_schema_has_first_response_latency_field_but_not_raw_ai_detail_fields(self) -> None:
        update_fields = set(UpdateSessionRequest.model_fields)
        response_fields = set(SessionResponse.model_fields)

        self.assertIn("first_response_latency_ms", update_fields)
        self.assertIn("first_response_latency_ms", response_fields)
        self.assertNotIn("fallback_mode", update_fields)
        self.assertNotIn("safety_tags", update_fields)


if __name__ == "__main__":
    unittest.main()
