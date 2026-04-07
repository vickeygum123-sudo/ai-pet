"""Minimal firmware-side models for MVP connectivity and voice-loop simulation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DeviceState(StrEnum):
    BOOTING = "booting"
    PAIRING_READY = "pairing_ready"
    CONNECTING_WIFI = "connecting_wifi"
    WIFI_CONNECTED = "wifi_connected"
    CONNECTING_CLOUD = "connecting_cloud"
    READY_TO_SPEAK = "ready_to_speak"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class DeviceErrorCode(StrEnum):
    WIFI_NOT_CONFIGURED = "wifi_not_configured"
    WIFI_CONNECT_FAILED = "wifi_connect_failed"
    CLOUD_CONNECT_FAILED = "cloud_connect_failed"
    AUDIO_CAPTURE_FAILED = "audio_capture_failed"
    CLOUD_REQUEST_FAILED = "cloud_request_failed"
    AUDIO_PLAYBACK_FAILED = "audio_playback_failed"
    CLOUD_AUDIO_MISSING = "cloud_audio_missing"


@dataclass(slots=True)
class WiFiCredentials:
    ssid: str
    password: str


@dataclass(slots=True)
class AudioFrame:
    payload: bytes
    audio_format: str = "audio/wav"
    sample_rate_hz: int = 16000
    channels: int = 1
    duration_ms: int | None = None


@dataclass(slots=True)
class VoiceTurnRequest:
    session_id: str
    request_id: str
    locale: str = "en-US"


@dataclass(slots=True)
class VoiceTurnResponse:
    transcript: str | None
    response_text: str
    audio: AudioFrame | None
    audio_format: str | None
    audio_url: str | None
    fallback_mode: str
    runtime_failure_code: str
    session_state: str


@dataclass(slots=True)
class DeviceSnapshot:
    device_id: str
    state: DeviceState
    wifi_connected: bool
    cloud_connected: bool
    current_session_id: str | None = None
    last_error: DeviceErrorCode | None = None
