from __future__ import annotations

from io import BytesIO
import unittest
import wave

from ai_orchestrator.audio import normalize_audio_input
from ai_orchestrator.contracts import AudioInput, ProviderError, VoiceLoopRequest
from ai_orchestrator.openai_asr import OpenAIASRProvider


class RecordingTransport:
    def __init__(self, response: dict[str, object] | None = None) -> None:
        self.response = response or {"text": "hello from real asr"}
        self.calls: list[dict[str, object]] = []

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        model: str,
        language: str | None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "audio_bytes": audio_bytes,
                "filename": filename,
                "content_type": content_type,
                "model": model,
                "language": language,
            }
        )
        return self.response


class OpenAIASRTests(unittest.TestCase):
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

    def test_normalize_audio_input_wraps_pcm_into_wav(self) -> None:
        normalized = normalize_audio_input(
            AudioInput(
                payload=b"\x00\x00\xe8\x03",
                audio_format="audio/pcm;codec=s16le;rate=16000;channels=1",
                sample_rate_hz=16000,
            )
        )

        self.assertEqual(normalized.audio_format, "audio/wav")
        self.assertEqual(normalized.filename, "input.wav")
        with wave.open(BytesIO(normalized.payload), "rb") as wav_file:
            self.assertEqual(wav_file.getnchannels(), 1)
            self.assertEqual(wav_file.getframerate(), 16000)
            self.assertEqual(wav_file.getsampwidth(), 2)
            self.assertEqual(wav_file.readframes(2), b"\x00\x00\xe8\x03")

    def test_openai_provider_normalizes_pcm_and_maps_locale_language(self) -> None:
        transport = RecordingTransport(response={"text": "I heard you clearly."})
        provider = OpenAIASRProvider(transport=transport, model="gpt-4o-mini-transcribe")

        result = provider.transcribe(self.make_request(payload=b"\x00\x00\xe8\x03"))

        self.assertEqual(result.transcript, "I heard you clearly.")
        self.assertEqual(result.provider, "openai:gpt-4o-mini-transcribe")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]["content_type"], "audio/wav")
        self.assertEqual(transport.calls[0]["filename"], "input.wav")
        self.assertEqual(transport.calls[0]["language"], "en")
        with wave.open(BytesIO(transport.calls[0]["audio_bytes"]), "rb") as wav_file:
            self.assertEqual(wav_file.getnchannels(), 1)
            self.assertEqual(wav_file.getframerate(), 16000)

    def test_openai_provider_passes_through_wav(self) -> None:
        normalized = normalize_audio_input(
            AudioInput(payload=b"RIFFdemo", audio_format="audio/wav", sample_rate_hz=16000)
        )
        self.assertEqual(normalized.payload, b"RIFFdemo")

    def test_openai_provider_rejects_unsupported_pcm_codec(self) -> None:
        provider = OpenAIASRProvider(transport=RecordingTransport())

        with self.assertRaises(ProviderError):
            provider.transcribe(
                self.make_request(
                    payload=b"\x00\x00\xe8\x03",
                    audio_format="audio/pcm;codec=mulaw;rate=16000;channels=1",
                )
            )

    def test_openai_provider_rejects_empty_transcript(self) -> None:
        provider = OpenAIASRProvider(transport=RecordingTransport(response={"text": "   "}))

        with self.assertRaises(ProviderError):
            provider.transcribe(self.make_request(payload=b"\x00\x00\xe8\x03"))


if __name__ == "__main__":
    unittest.main()
