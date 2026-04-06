from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import wave

from .contracts import AudioInput, ProviderError


WAV_AUDIO_FORMATS = {"audio/wav", "audio/x-wav", "audio/wave"}


@dataclass(slots=True)
class NormalizedAudio:
    payload: bytes
    audio_format: str
    filename: str


def normalize_audio_input(audio: AudioInput) -> NormalizedAudio:
    media_type, params = _parse_audio_format(audio.audio_format)
    if media_type in WAV_AUDIO_FORMATS:
        return NormalizedAudio(payload=audio.payload, audio_format="audio/wav", filename="input.wav")

    if media_type == "audio/pcm":
        codec = params.get("codec", "s16le")
        channels = _coerce_positive_int(params.get("channels"), default=1, field_name="channels")
        sample_rate_hz = audio.sample_rate_hz or _coerce_positive_int(
            params.get("rate"),
            default=16000,
            field_name="rate",
        )
        return NormalizedAudio(
            payload=pcm_s16le_to_wav(
                audio.payload,
                sample_rate_hz=sample_rate_hz,
                channels=channels,
                codec=codec,
            ),
            audio_format="audio/wav",
            filename="input.wav",
        )

    raise ProviderError(f"unsupported audio format for ASR provider: {audio.audio_format}")


def pcm_s16le_to_wav(
    audio_bytes: bytes,
    *,
    sample_rate_hz: int,
    channels: int,
    codec: str = "s16le",
) -> bytes:
    if codec.lower() != "s16le":
        raise ProviderError(f"unsupported PCM codec for WAV normalization: {codec}")

    frame_width = channels * 2
    if len(audio_bytes) % frame_width != 0:
        raise ProviderError("PCM payload length does not align with 16-bit frame size")

    wav_buffer = BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(audio_bytes)
    return wav_buffer.getvalue()


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
