from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any, Callable, Protocol
from urllib import error, request

from .audio import WAV_AUDIO_FORMATS, normalize_audio_input
from .contracts import ASRResult, AudioInput, ProviderError, VoiceLoopRequest


TENCENT_ASR_ACTION = "SentenceRecognition"
TENCENT_ASR_VERSION = "2019-06-14"
TENCENT_ASR_SERVICE = "asr"
TENCENT_ASR_CONTENT_TYPE = "application/json; charset=utf-8"


@dataclass(slots=True)
class TencentTranscriptionAudio:
    payload: bytes
    voice_format: str
    input_sample_rate: int | None = None


class TencentSentenceRecognitionTransport(Protocol):
    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        voice_format: str,
        engine_model_type: str,
        input_sample_rate: int | None,
    ) -> dict[str, Any]:
        ...


class TencentCloudSentenceRecognitionHTTPTransport:
    def __init__(
        self,
        *,
        secret_id: str,
        secret_key: str,
        endpoint: str = "https://asr.tencentcloudapi.com",
        region: str = "ap-shanghai",
        timeout_seconds: float = 20.0,
        project_id: int = 0,
        sub_service_type: int = 2,
        word_info: int = 0,
        filter_dirty: int = 0,
        filter_modal: int = 0,
        filter_punc: int = 0,
        convert_num_mode: int = 1,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._endpoint = endpoint.rstrip("/")
        self._region = region.strip()
        self._timeout_seconds = timeout_seconds
        self._project_id = project_id
        self._sub_service_type = sub_service_type
        self._word_info = word_info
        self._filter_dirty = filter_dirty
        self._filter_modal = filter_modal
        self._filter_punc = filter_punc
        self._convert_num_mode = convert_num_mode
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        voice_format: str,
        engine_model_type: str,
        input_sample_rate: int | None,
    ) -> dict[str, Any]:
        body = {
            "ProjectId": self._project_id,
            "SubServiceType": self._sub_service_type,
            "EngSerViceType": engine_model_type,
            "SourceType": 1,
            "VoiceFormat": voice_format,
            "Data": base64.b64encode(audio_bytes).decode("ascii"),
            "DataLen": len(audio_bytes),
            "WordInfo": self._word_info,
            "FilterDirty": self._filter_dirty,
            "FilterModal": self._filter_modal,
            "FilterPunc": self._filter_punc,
            "ConvertNumMode": self._convert_num_mode,
        }
        if input_sample_rate is not None:
            body["InputSampleRate"] = input_sample_rate

        payload = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        timestamp = int(self._clock().timestamp())
        http_request = request.Request(
            url=f"{self._endpoint}/",
            data=payload,
            headers=self._build_headers(payload=payload, timestamp=timestamp),
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(
                f"tencent transcription request failed with status {exc.code}: {detail[:200]}"
            ) from exc
        except error.URLError as exc:
            raise ProviderError("tencent transcription request failed") from exc
        except json.JSONDecodeError as exc:
            raise ProviderError("tencent transcription returned invalid JSON") from exc

        response_body = parsed.get("Response", {})
        error_body = response_body.get("Error")
        if error_body:
            code = str(error_body.get("Code", "UnknownError")).strip() or "UnknownError"
            message = str(error_body.get("Message", "Tencent ASR request failed")).strip()
            request_id = str(response_body.get("RequestId", "")).strip()
            suffix = f" (request_id={request_id})" if request_id else ""
            raise TencentASRResponseError(
                f"tencent transcription failed: {code}: {message}{suffix}",
                response_body=response_body,
            )

        return response_body

    def _build_headers(self, *, payload: bytes, timestamp: int) -> dict[str, str]:
        authorization = _build_tc3_authorization(
            secret_id=self._secret_id,
            secret_key=self._secret_key,
            service=TENCENT_ASR_SERVICE,
            host=_extract_host(self._endpoint),
            payload=payload,
            timestamp=timestamp,
        )
        headers = {
            "Authorization": authorization,
            "Content-Type": TENCENT_ASR_CONTENT_TYPE,
            "Host": _extract_host(self._endpoint),
            "X-TC-Action": TENCENT_ASR_ACTION,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": TENCENT_ASR_VERSION,
        }
        if self._region:
            headers["X-TC-Region"] = self._region
        return headers


class TencentASRProvider:
    def __init__(
        self,
        *,
        transport: TencentSentenceRecognitionTransport,
        default_engine_model_type: str = "16k_zh",
        provider_name: str = "tencent",
    ) -> None:
        self._transport = transport
        self._default_engine_model_type = default_engine_model_type
        self._provider_name = provider_name

    def transcribe(self, request: VoiceLoopRequest) -> ASRResult:
        if not request.audio.payload:
            raise ProviderError("empty audio payload")

        try:
            prepared_audio = prepare_tencent_audio(request.audio)
        except ProviderError:
            raise
        engine_model_type = locale_to_tencent_engine_model_type(
            request.locale,
            default_engine_model_type=self._default_engine_model_type,
        )
        response = self._transport.transcribe(
            audio_bytes=prepared_audio.payload,
            voice_format=prepared_audio.voice_format,
            engine_model_type=engine_model_type,
            input_sample_rate=prepared_audio.input_sample_rate,
        )

        transcript = str(response.get("Result", "")).strip()
        if not transcript:
            raise ProviderError("tencent transcription returned empty result")

        return ASRResult(
            transcript=transcript,
            confidence=0.0,
            provider=f"{self._provider_name}:{engine_model_type}",
        )


class TencentASRResponseError(ProviderError):
    def __init__(self, message: str, *, response_body: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.response_body = response_body


def prepare_tencent_audio(audio: AudioInput) -> TencentTranscriptionAudio:
    media_type, params = _parse_audio_format(audio.audio_format)
    if media_type in WAV_AUDIO_FORMATS:
        return TencentTranscriptionAudio(payload=audio.payload, voice_format="wav")

    if media_type == "audio/pcm":
        codec = params.get("codec", "s16le")
        channels = _coerce_positive_int(params.get("channels"), default=1, field_name="channels")
        sample_rate_hz = audio.sample_rate_hz or _coerce_positive_int(
            params.get("rate"),
            default=16000,
            field_name="rate",
        )
        if codec == "s16le" and channels == 1 and sample_rate_hz in {8000, 16000}:
            input_sample_rate = sample_rate_hz if sample_rate_hz == 8000 else None
            return TencentTranscriptionAudio(
                payload=audio.payload,
                voice_format="pcm",
                input_sample_rate=input_sample_rate,
            )

    normalized_audio = normalize_audio_input(audio)
    return TencentTranscriptionAudio(
        payload=normalized_audio.payload,
        voice_format="wav",
    )


def locale_to_tencent_engine_model_type(
    locale: str | None,
    *,
    default_engine_model_type: str = "16k_zh",
) -> str:
    if locale is None:
        return default_engine_model_type

    cleaned = locale.strip()
    if not cleaned:
        return default_engine_model_type

    primary_subtag = cleaned.replace("_", "-").split("-", 1)[0].strip().lower()
    return {
        "zh": "16k_zh",
        "en": "16k_en",
        "ja": "16k_ja",
        "ko": "16k_ko",
        "yue": "16k_yue",
    }.get(primary_subtag, default_engine_model_type)


def _build_tc3_authorization(
    *,
    secret_id: str,
    secret_key: str,
    service: str,
    host: str,
    payload: bytes,
    timestamp: int,
) -> str:
    algorithm = "TC3-HMAC-SHA256"
    canonical_headers = f"content-type:{TENCENT_ASR_CONTENT_TYPE}\nhost:{host}\n"
    signed_headers = "content-type;host"
    hashed_request_payload = _sha256_hex(payload)
    canonical_request = "\n".join(
        (
            "POST",
            "/",
            "",
            canonical_headers,
            signed_headers,
            hashed_request_payload,
        )
    )
    date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    credential_scope = f"{date}/{service}/tc3_request"
    string_to_sign = "\n".join(
        (
            algorithm,
            str(timestamp),
            credential_scope,
            _sha256_hex(canonical_request.encode("utf-8")),
        )
    )

    secret_date = _sign_hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _sign_hmac_sha256(secret_date, service)
    secret_signing = _sign_hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return (
        f"{algorithm} Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )


def _sign_hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _extract_host(endpoint: str) -> str:
    cleaned = endpoint.strip().rstrip("/")
    if "://" in cleaned:
        cleaned = cleaned.split("://", 1)[1]
    return cleaned.split("/", 1)[0]


def _parse_audio_format(audio_format: str) -> tuple[str, dict[str, str]]:
    parts = [part.strip() for part in audio_format.split(";") if part.strip()]
    if not parts:
        raise ProviderError("audio format is required")

    media_type = parts[0].lower()
    params: dict[str, str] = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        params[key.strip().lower()] = value.strip().strip('"').lower()
    return media_type, params


def _coerce_positive_int(value: str | None, *, default: int, field_name: str) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ProviderError(f"invalid {field_name} parameter in audio format: {value}") from exc

    if parsed <= 0:
        raise ProviderError(f"{field_name} parameter must be positive")
    return parsed
