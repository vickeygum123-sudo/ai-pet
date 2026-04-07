"""Cloud adapters for the MVP firmware simulator."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import error, request

from .connectivity import CloudConnectionAdapter, CloudConnectionError
from .models import AudioFrame, VoiceTurnRequest, VoiceTurnResponse


class CloudRequestError(RuntimeError):
    """Raised when the MVP device gateway request cannot be completed."""


class JSONTransport(Protocol):
    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send JSON to a cloud endpoint and return the decoded JSON response."""

    def get_bytes(self, path: str) -> tuple[bytes, str | None]:
        """Fetch raw bytes from a cloud endpoint and return bytes plus content type."""


@dataclass(slots=True)
class HTTPJSONTransport:
    """Small standard-library HTTP transport for MVP local integration."""

    base_url: str
    timeout_seconds: float = 10.0

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=self._resolve_url(path),
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise CloudRequestError("firmware cloud request failed") from exc

    def get_bytes(self, path: str) -> tuple[bytes, str | None]:
        req = request.Request(url=self._resolve_url(path), method="GET")
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return response.read(), response.headers.get("Content-Type")
        except error.URLError as exc:
            raise CloudRequestError("firmware cloud audio request failed") from exc

    def _resolve_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url.rstrip('/')}{path}"


@dataclass(slots=True)
class JSONTransportCloudConnectionAdapter:
    """Uses the configured transport to confirm the cloud base URL is reachable."""

    transport: JSONTransport

    def connect(self) -> None:
        try:
            self.transport.post_json("/__connectivity_probe__", {"probe": True})
        except CloudRequestError as exc:
            raise CloudConnectionError("cloud connectivity probe failed") from exc


@dataclass(slots=True)
class BackendVoiceLoopGateway:
    """Firmware-side adapter for the current MVP internal JSON/base64 voice-loop route."""

    transport: JSONTransport

    def run_voice_loop(self, turn: VoiceTurnRequest, audio: AudioFrame) -> VoiceTurnResponse:
        payload = {
            "requestId": turn.request_id,
            "audioBase64": base64.b64encode(audio.payload).decode("ascii"),
            "audioFormat": audio.audio_format,
            "sampleRateHz": audio.sample_rate_hz,
            "durationMs": audio.duration_ms,
            "locale": turn.locale,
        }
        try:
            response = self.transport.post_json(
                f"/v1/internal/device-sessions/{turn.session_id}/voice-loop",
                payload,
            )
        except CloudRequestError:
            raise
        except Exception as exc:  # pragma: no cover - defensive adapter boundary
            raise CloudRequestError("unexpected cloud transport failure") from exc

        encoded_audio = response.get("audioBase64")
        audio_frame = None
        audio_format = response.get("audioFormat")
        audio_url = response.get("audioUrl")
        if encoded_audio is not None:
            audio_frame = AudioFrame(
                payload=base64.b64decode(encoded_audio),
                audio_format=audio_format or "audio/wav",
                sample_rate_hz=audio.sample_rate_hz,
                channels=audio.channels,
            )
        elif audio_url:
            audio_bytes, downloaded_content_type = self.transport.get_bytes(str(audio_url))
            resolved_audio_format = audio_format or downloaded_content_type or "audio/wav"
            audio_frame = AudioFrame(
                payload=audio_bytes,
                audio_format=resolved_audio_format,
                sample_rate_hz=audio.sample_rate_hz,
                channels=audio.channels,
            )
            audio_format = resolved_audio_format

        session = response.get("session") or {}
        return VoiceTurnResponse(
            transcript=response.get("transcript"),
            response_text=str(response.get("responseText", "")),
            audio=audio_frame,
            audio_format=audio_format,
            audio_url=str(audio_url) if audio_url is not None else None,
            fallback_mode=str(response.get("fallbackMode", "none")),
            runtime_failure_code=str(response.get("runtimeFailureCode", "unknown")),
            session_state=str(session.get("state", "unknown")),
        )
