from __future__ import annotations

import base64
import json
from typing import Any, Protocol
from urllib import error, request
from uuid import uuid4

from .contracts import ProviderError, TTSResult, VoiceLoopRequest


VOLCENGINE_TTS_SUCCESS_CODE = 20000000
VOLCENGINE_TTS_AUDIO_CHUNK_CODE = 0


class VolcengineTTSTransport(Protocol):
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
    ) -> list[dict[str, Any]]:
        ...


class VolcengineHTTPSSETTSTransport:
    def __init__(
        self,
        *,
        endpoint: str = "https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse",
        timeout_seconds: float = 20.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._timeout_seconds = timeout_seconds

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
    ) -> list[dict[str, Any]]:
        req_params: dict[str, object] = {
            "text": text,
            "speaker": speaker,
            "audio_params": {
                "format": audio_format,
                "sample_rate": sample_rate,
            },
        }
        if model:
            req_params["model"] = model

        payload = {
            "user": {"uid": uid},
            "req_params": req_params,
        }

        http_request = request.Request(
            url=self._endpoint,
            data=json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
            headers={
                "X-Api-App-Id": appid,
                "X-Api-Access-Key": access_key,
                "X-Api-Resource-Id": resource_id,
                "X-Api-Request-Id": str(uuid4()),
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                return _parse_sse_payload(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(
                f"volcengine tts v3 request failed with status {exc.code}: {detail[:200]}"
            ) from exc
        except error.URLError as exc:
            raise ProviderError("volcengine tts v3 request failed") from exc
        except json.JSONDecodeError as exc:
            raise ProviderError("volcengine tts v3 returned invalid JSON") from exc


class VolcengineTTSProvider:
    def __init__(
        self,
        *,
        transport: VolcengineTTSTransport,
        appid: str,
        access_key: str,
        resource_id: str = "seed-tts-2.0",
        provider_name: str = "volcengine",
        audio_format: str = "wav",
        sample_rate: int = 24000,
        default_voice_type: str = "zh_female_vv_uranus_bigtts",
        default_uid: str = "ai-pet-server",
        model: str | None = None,
        voice_map: dict[str, str] | None = None,
    ) -> None:
        self._transport = transport
        self._appid = appid
        self._access_key = access_key
        self._resource_id = resource_id.strip()
        self._provider_name = provider_name
        self._audio_format = audio_format.strip().lower()
        self._sample_rate = sample_rate
        self._default_voice_type = default_voice_type.strip()
        self._default_uid = default_uid.strip()
        self._model = model.strip() if model else None
        self._voice_map = {
            voice_id.strip(): voice_type.strip()
            for voice_id, voice_type in (voice_map or {}).items()
            if voice_id.strip() and voice_type.strip()
        }

    def synthesize(self, text: str, voice_id: str, request: VoiceLoopRequest) -> TTSResult:
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ProviderError("empty tts text")

        events = self._transport.synthesize(
            appid=self._appid,
            access_key=self._access_key,
            resource_id=self._resource_id,
            uid=_build_uid(request, fallback=self._default_uid),
            text=cleaned_text,
            speaker=self._resolve_voice_type(voice_id),
            audio_format=self._audio_format,
            sample_rate=self._sample_rate,
            model=self._model,
        )

        audio_chunks: list[bytes] = []
        saw_finish = False
        for event in events:
            code = int(event.get("code", -1))
            if code == VOLCENGINE_TTS_AUDIO_CHUNK_CODE:
                encoded_audio = event.get("data")
                if encoded_audio is None:
                    continue
                encoded_audio_str = str(encoded_audio).strip()
                if not encoded_audio_str:
                    continue
                try:
                    audio_chunks.append(base64.b64decode(encoded_audio_str, validate=True))
                except (ValueError, TypeError) as exc:
                    raise ProviderError("volcengine tts v3 returned invalid base64 audio") from exc
                continue

            if code == VOLCENGINE_TTS_SUCCESS_CODE:
                saw_finish = True
                continue

            message = str(event.get("message", "volcengine tts v3 failed")).strip()
            raise ProviderError(f"volcengine tts v3 failed: code={code}: {message}")

        if not saw_finish:
            raise ProviderError("volcengine tts v3 did not finish successfully")
        if not audio_chunks:
            raise ProviderError("volcengine tts v3 returned empty audio")

        return TTSResult(
            audio_bytes=b"".join(audio_chunks),
            audio_format=_encoding_to_audio_format(self._audio_format),
            provider=f"{self._provider_name}:{self._resource_id}",
            voice_id=self._resolve_voice_type(voice_id),
        )

    def _resolve_voice_type(self, voice_id: str) -> str:
        cleaned_voice_id = voice_id.strip()
        if cleaned_voice_id in self._voice_map:
            return self._voice_map[cleaned_voice_id]
        return cleaned_voice_id or self._default_voice_type


def _parse_sse_payload(payload: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if not line.startswith("{"):
            continue
        events.append(json.loads(line))
    return events


def _encoding_to_audio_format(encoding: str) -> str:
    return {
        "pcm": "audio/pcm",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "ogg_opus": "audio/ogg",
    }.get(encoding, "audio/mpeg")


def _build_uid(request: VoiceLoopRequest, *, fallback: str) -> str:
    parts = [request.user_id.strip(), request.device_id.strip()]
    joined = "-".join(part for part in parts if part)
    return joined[:128] or fallback
