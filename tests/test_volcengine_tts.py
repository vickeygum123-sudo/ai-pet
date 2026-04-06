from __future__ import annotations

import base64
import unittest

from ai_orchestrator.contracts import AudioInput, VoiceLoopRequest
from ai_orchestrator.volcengine_tts import VolcengineTTSProvider


class RecordingTransport:
    def __init__(self, response: list[dict[str, object]] | None = None) -> None:
        self.response = response or [
            {"code": 0, "message": "", "data": base64.b64encode(b"RIFF....WAVE").decode("ascii")},
            {"code": 20000000, "message": "OK", "data": None},
        ]
        self.calls: list[dict[str, object]] = []

    def synthesize(
        self,
        *,
        appid: str,
        access_key: str,
        resource_id: str,
        uid: str,
        text: str,
        speaker: str,
        audio_format: str,
        sample_rate: int,
        model: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "appid": appid,
                "access_key": access_key,
                "resource_id": resource_id,
                "uid": uid,
                "text": text,
                "speaker": speaker,
                "audio_format": audio_format,
                "sample_rate": sample_rate,
                "model": model,
            }
        )
        return self.response


class VolcengineTTSProviderTests(unittest.TestCase):
    def make_request(self) -> VoiceLoopRequest:
        return VoiceLoopRequest(
            request_id="req-1",
            user_id="user-1",
            device_id="device-1",
            session_id="session-1",
            audio=AudioInput(payload=b"test"),
        )

    def test_provider_maps_internal_voice_to_volcengine_voice_type(self) -> None:
        transport = RecordingTransport()
        provider = VolcengineTTSProvider(
            transport=transport,
            appid="appid",
            access_key="access-key",
            default_voice_type="zh_female_vv_uranus_bigtts",
            voice_map={"companion-calm-v1": "zh_female_vv_uranus_bigtts"},
        )

        result = provider.synthesize("I am here with you.", "companion-calm-v1", self.make_request())

        self.assertEqual(result.audio_bytes, b"RIFF....WAVE")
        self.assertEqual(result.audio_format, "audio/wav")
        self.assertEqual(result.voice_id, "zh_female_vv_uranus_bigtts")
        self.assertEqual(transport.calls[0]["speaker"], "zh_female_vv_uranus_bigtts")
        self.assertEqual(transport.calls[0]["resource_id"], "seed-tts-2.0")

    def test_provider_accepts_direct_voice_type(self) -> None:
        transport = RecordingTransport(
            response=[
                {"code": 0, "message": "", "data": base64.b64encode(b"\x00").decode("ascii")},
                {"code": 0, "message": "", "data": base64.b64encode(b"\x00").decode("ascii")},
                {"code": 20000000, "message": "OK", "data": None},
            ]
        )
        provider = VolcengineTTSProvider(
            transport=transport,
            appid="appid",
            access_key="access-key",
            audio_format="pcm",
        )

        result = provider.synthesize("hello", "zh_male_m191_uranus_bigtts", self.make_request())

        self.assertEqual(result.voice_id, "zh_male_m191_uranus_bigtts")
        self.assertEqual(result.audio_format, "audio/pcm")
        self.assertEqual(result.audio_bytes, b"\x00\x00")

    def test_provider_rejects_non_success_code(self) -> None:
        provider = VolcengineTTSProvider(
            transport=RecordingTransport(response=[{"code": 45000000, "message": "speaker permission denied"}]),
            appid="appid",
            access_key="access-key",
        )

        with self.assertRaisesRegex(RuntimeError, "code=45000000"):
            provider.synthesize("hello", "companion-calm-v1", self.make_request())

    def test_provider_rejects_invalid_base64(self) -> None:
        provider = VolcengineTTSProvider(
            transport=RecordingTransport(
                response=[
                    {"code": 0, "message": "", "data": "not-base64"},
                    {"code": 20000000, "message": "OK", "data": None},
                ]
            ),
            appid="appid",
            access_key="access-key",
        )

        with self.assertRaisesRegex(RuntimeError, "invalid base64"):
            provider.synthesize("hello", "companion-calm-v1", self.make_request())

    def test_provider_rejects_missing_finish_event(self) -> None:
        provider = VolcengineTTSProvider(
            transport=RecordingTransport(
                response=[{"code": 0, "message": "", "data": base64.b64encode(b"a").decode("ascii")}]
            ),
            appid="appid",
            access_key="access-key",
        )

        with self.assertRaisesRegex(RuntimeError, "did not finish"):
            provider.synthesize("hello", "companion-calm-v1", self.make_request())


if __name__ == "__main__":
    unittest.main()
