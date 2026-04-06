from __future__ import annotations

from datetime import datetime, timezone
import json
import unittest
from unittest.mock import patch

from ai_orchestrator.contracts import AudioInput, ProviderError, VoiceLoopRequest
from ai_orchestrator.tencent_asr import (
    TencentASRProvider,
    TencentCloudSentenceRecognitionHTTPTransport,
    locale_to_tencent_engine_model_type,
)


class RecordingTransport:
    def __init__(self, response: dict[str, object] | None = None) -> None:
        self.response = response or {"Result": "hello from tencent asr"}
        self.calls: list[dict[str, object]] = []

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        voice_format: str,
        engine_model_type: str,
        input_sample_rate: int | None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "audio_bytes": audio_bytes,
                "voice_format": voice_format,
                "engine_model_type": engine_model_type,
                "input_sample_rate": input_sample_rate,
            }
        )
        return self.response


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class TencentASRTests(unittest.TestCase):
    def make_request(
        self,
        *,
        payload: bytes,
        audio_format: str = "audio/pcm;codec=s16le;rate=16000;channels=1",
        sample_rate_hz: int = 16000,
        locale: str = "en-US",
    ) -> VoiceLoopRequest:
        return VoiceLoopRequest(
            request_id="req-1",
            user_id="user-1",
            device_id="device-1",
            session_id="session-1",
            audio=AudioInput(
                payload=payload,
                audio_format=audio_format,
                sample_rate_hz=sample_rate_hz,
            ),
            locale=locale,
        )

    def test_provider_prefers_direct_pcm_for_board_audio(self) -> None:
        transport = RecordingTransport(response={"Result": "I heard you clearly."})
        provider = TencentASRProvider(transport=transport, default_engine_model_type="16k_zh")

        result = provider.transcribe(self.make_request(payload=b"\x00\x00\xe8\x03", locale="en-US"))

        self.assertEqual(result.transcript, "I heard you clearly.")
        self.assertEqual(result.provider, "tencent:16k_en")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]["voice_format"], "pcm")
        self.assertEqual(transport.calls[0]["audio_bytes"], b"\x00\x00\xe8\x03")
        self.assertIsNone(transport.calls[0]["input_sample_rate"])

    def test_provider_falls_back_to_wav_normalization_when_pcm_shape_is_not_directly_supported(self) -> None:
        transport = RecordingTransport()
        provider = TencentASRProvider(transport=transport)

        provider.transcribe(
            self.make_request(
                payload=b"\x00\x00\xe8\x03\x10\x00\xf0\xff",
                audio_format="audio/pcm;codec=s16le;rate=16000;channels=2",
            )
        )

        self.assertEqual(transport.calls[0]["voice_format"], "wav")
        self.assertTrue(bytes(transport.calls[0]["audio_bytes"]).startswith(b"RIFF"))

    def test_provider_passes_through_wav_audio(self) -> None:
        transport = RecordingTransport()
        provider = TencentASRProvider(transport=transport)

        provider.transcribe(self.make_request(payload=b"RIFFdemo", audio_format="audio/wav"))

        self.assertEqual(transport.calls[0]["voice_format"], "wav")
        self.assertEqual(transport.calls[0]["audio_bytes"], b"RIFFdemo")

    def test_provider_rejects_empty_transcript(self) -> None:
        provider = TencentASRProvider(transport=RecordingTransport(response={"Result": "   "}))

        with self.assertRaises(ProviderError):
            provider.transcribe(self.make_request(payload=b"\x00\x00\xe8\x03"))

    def test_locale_to_tencent_engine_model_type_uses_known_mappings(self) -> None:
        self.assertEqual(
            locale_to_tencent_engine_model_type("en-US", default_engine_model_type="16k_zh"),
            "16k_en",
        )
        self.assertEqual(
            locale_to_tencent_engine_model_type("zh-CN", default_engine_model_type="16k_en"),
            "16k_zh",
        )
        self.assertEqual(
            locale_to_tencent_engine_model_type("fr-FR", default_engine_model_type="16k_zh"),
            "16k_zh",
        )

    def test_http_transport_builds_signed_request_and_returns_response_body(self) -> None:
        captured_request = None

        def fake_urlopen(http_request, timeout: float):
            nonlocal captured_request
            captured_request = http_request
            self.assertEqual(timeout, 5.0)
            return FakeHTTPResponse({"Response": {"Result": "signed transport transcript"}})

        transport = TencentCloudSentenceRecognitionHTTPTransport(
            secret_id="secret-id",
            secret_key="secret-key",
            region="ap-shanghai",
            timeout_seconds=5.0,
            clock=lambda: datetime(2024, 1, 2, tzinfo=timezone.utc),
        )

        with patch("ai_orchestrator.tencent_asr.request.urlopen", side_effect=fake_urlopen):
            response = transport.transcribe(
                audio_bytes=b"\x00\x00\xe8\x03",
                voice_format="pcm",
                engine_model_type="16k_en",
                input_sample_rate=None,
            )

        self.assertEqual(response["Result"], "signed transport transcript")
        self.assertIsNotNone(captured_request)
        headers = {key.lower(): value for key, value in captured_request.header_items()}
        self.assertEqual(headers["x-tc-action"], "SentenceRecognition")
        self.assertEqual(headers["x-tc-version"], "2019-06-14")
        self.assertEqual(headers["x-tc-timestamp"], str(int(datetime(2024, 1, 2, tzinfo=timezone.utc).timestamp())))
        self.assertEqual(headers["x-tc-region"], "ap-shanghai")
        self.assertIn("TC3-HMAC-SHA256 Credential=secret-id/2024-01-02/asr/tc3_request", headers["authorization"])

        payload = json.loads(captured_request.data.decode("utf-8"))
        self.assertEqual(payload["VoiceFormat"], "pcm")
        self.assertEqual(payload["EngSerViceType"], "16k_en")
        self.assertEqual(payload["DataLen"], 4)


if __name__ == "__main__":
    unittest.main()
