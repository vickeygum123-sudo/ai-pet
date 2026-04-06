from __future__ import annotations

import json
from typing import Any, Protocol
from urllib import error, request
from uuid import uuid4

from .audio import normalize_audio_input
from .contracts import ASRResult, ProviderError, VoiceLoopRequest


class OpenAITranscriptionTransport(Protocol):
    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        model: str,
        language: str | None,
    ) -> dict[str, Any]:
        ...


class OpenAIHTTPTranscriptionTransport:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 20.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        model: str,
        language: str | None,
    ) -> dict[str, Any]:
        body, boundary = _encode_multipart_form_data(
            fields=[
                ("model", model),
                ("response_format", "json"),
                *([("language", language)] if language else []),
            ],
            file_field_name="file",
            filename=filename,
            file_bytes=audio_bytes,
            content_type=content_type,
        )
        http_request = request.Request(
            url=f"{self._base_url}/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(
                f"openai transcription request failed with status {exc.code}: {detail[:200]}"
            ) from exc
        except error.URLError as exc:
            raise ProviderError("openai transcription request failed") from exc
        except json.JSONDecodeError as exc:
            raise ProviderError("openai transcription returned invalid JSON") from exc


class OpenAIASRProvider:
    def __init__(
        self,
        *,
        transport: OpenAITranscriptionTransport,
        model: str = "gpt-4o-mini-transcribe",
        provider_name: str = "openai",
    ) -> None:
        self._transport = transport
        self._model = model
        self._provider_name = provider_name

    def transcribe(self, request: VoiceLoopRequest) -> ASRResult:
        if not request.audio.payload:
            raise ProviderError("empty audio payload")

        normalized_audio = normalize_audio_input(request.audio)
        language = locale_to_language_code(request.locale)

        response = self._transport.transcribe(
            audio_bytes=normalized_audio.payload,
            filename=normalized_audio.filename,
            content_type=normalized_audio.audio_format,
            model=self._model,
            language=language,
        )
        transcript = str(response.get("text", "")).strip()
        if not transcript:
            raise ProviderError("openai transcription returned empty text")

        return ASRResult(
            transcript=transcript,
            confidence=0.0,
            provider=f"{self._provider_name}:{self._model}",
        )


def locale_to_language_code(locale: str | None) -> str | None:
    if locale is None:
        return None

    cleaned = locale.strip()
    if not cleaned:
        return None

    primary_subtag = cleaned.replace("_", "-").split("-", 1)[0].strip().lower()
    return primary_subtag or None


def _encode_multipart_form_data(
    *,
    fields: list[tuple[str, str]],
    file_field_name: str,
    filename: str,
    file_bytes: bytes,
    content_type: str,
) -> tuple[bytes, str]:
    boundary = f"codex-{uuid4().hex}"
    body = bytearray()

    for name, value in fields:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (
            f'Content-Disposition: form-data; name="{file_field_name}"; '
            f'filename="{filename}"\r\n'
        ).encode("utf-8")
    )
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), boundary
