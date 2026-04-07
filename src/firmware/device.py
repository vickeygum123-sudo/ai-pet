"""Minimal firmware device state machine for MVP local integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .audio import AudioCaptureError, AudioInput, AudioOutput, AudioPlaybackError
from .cloud import BackendVoiceLoopGateway, CloudRequestError
from .connectivity import (
    CloudConnectionAdapter,
    CloudConnectionError,
    WiFiAdapter,
    WiFiConnectionError,
)
from .models import (
    DeviceErrorCode,
    DeviceSnapshot,
    DeviceState,
    VoiceTurnRequest,
    VoiceTurnResponse,
    WiFiCredentials,
)


class DeviceStatusReporter(Protocol):
    def report(self, snapshot: DeviceSnapshot) -> None:
        """Persist or emit a point-in-time device snapshot."""


@dataclass(slots=True)
class InMemoryDeviceStatusReporter:
    """Collects device snapshots for tests and local inspection."""

    snapshots: list[DeviceSnapshot] = field(default_factory=list)

    def report(self, snapshot: DeviceSnapshot) -> None:
        self.snapshots.append(snapshot)


@dataclass(slots=True)
class NullDeviceStatusReporter:
    """No-op device reporter used when telemetry hooks are not wired yet."""

    def report(self, snapshot: DeviceSnapshot) -> None:
        _ = snapshot


@dataclass(slots=True)
class FirmwareDevice:
    """Lightweight firmware runtime focused on connectivity, audio I/O, and cloud handoff."""

    device_id: str
    wifi_adapter: WiFiAdapter
    cloud_connection: CloudConnectionAdapter
    audio_input: AudioInput
    audio_output: AudioOutput
    voice_gateway: BackendVoiceLoopGateway
    status_reporter: DeviceStatusReporter = field(default_factory=NullDeviceStatusReporter)

    state: DeviceState = field(init=False, default=DeviceState.BOOTING)
    wifi_connected: bool = field(init=False, default=False)
    cloud_connected: bool = field(init=False, default=False)
    current_session_id: str | None = field(init=False, default=None)
    last_error: DeviceErrorCode | None = field(init=False, default=None)
    booted: bool = field(init=False, default=False)

    def boot(self) -> DeviceSnapshot:
        self.booted = True
        self.state = DeviceState.BOOTING
        self._emit_snapshot()
        return self._transition(DeviceState.PAIRING_READY)

    def provision_wifi(self, credentials: WiFiCredentials) -> DeviceSnapshot:
        self._ensure_booted()
        self.last_error = None
        self._transition(DeviceState.CONNECTING_WIFI)
        try:
            self.wifi_adapter.connect(credentials)
        except WiFiConnectionError as exc:
            raise self._fail(DeviceErrorCode.WIFI_CONNECT_FAILED, exc) from exc

        self.wifi_connected = True
        return self._transition(DeviceState.WIFI_CONNECTED)

    def connect_cloud(self) -> DeviceSnapshot:
        self._ensure_booted()
        if not self.wifi_connected:
            raise self._fail(DeviceErrorCode.WIFI_NOT_CONFIGURED)

        self.last_error = None
        self._transition(DeviceState.CONNECTING_CLOUD)
        try:
            self.cloud_connection.connect()
        except CloudConnectionError as exc:
            raise self._fail(DeviceErrorCode.CLOUD_CONNECT_FAILED, exc) from exc

        self.cloud_connected = True
        return self._transition(DeviceState.READY_TO_SPEAK)

    def run_voice_turn(self, turn: VoiceTurnRequest) -> VoiceTurnResponse:
        self._ensure_booted()
        if not self.wifi_connected:
            raise self._fail(DeviceErrorCode.WIFI_NOT_CONFIGURED)
        if not self.cloud_connected:
            raise self._fail(DeviceErrorCode.CLOUD_CONNECT_FAILED)

        self.current_session_id = turn.session_id
        self.last_error = None
        self._transition(DeviceState.LISTENING)
        try:
            audio = self.audio_input.capture()
        except AudioCaptureError as exc:
            raise self._fail(DeviceErrorCode.AUDIO_CAPTURE_FAILED, exc) from exc

        self._transition(DeviceState.THINKING)
        try:
            response = self.voice_gateway.run_voice_loop(turn, audio)
        except CloudRequestError as exc:
            raise self._fail(DeviceErrorCode.CLOUD_REQUEST_FAILED, exc) from exc

        if response.audio is None:
            raise self._fail(DeviceErrorCode.CLOUD_AUDIO_MISSING)

        self._transition(DeviceState.SPEAKING)
        try:
            self.audio_output.play(response.audio)
        except AudioPlaybackError as exc:
            raise self._fail(DeviceErrorCode.AUDIO_PLAYBACK_FAILED, exc) from exc

        self.current_session_id = None
        self.last_error = None
        self._transition(DeviceState.READY_TO_SPEAK)
        return response

    def _ensure_booted(self) -> None:
        if not self.booted:
            self.boot()

    def _transition(self, state: DeviceState) -> DeviceSnapshot:
        self.state = state
        return self._emit_snapshot()

    def _emit_snapshot(self) -> DeviceSnapshot:
        snapshot = DeviceSnapshot(
            device_id=self.device_id,
            state=self.state,
            wifi_connected=self.wifi_connected,
            cloud_connected=self.cloud_connected,
            current_session_id=self.current_session_id,
            last_error=self.last_error,
        )
        self.status_reporter.report(snapshot)
        return snapshot

    def _fail(
        self,
        error_code: DeviceErrorCode,
        cause: Exception | None = None,
    ) -> RuntimeError:
        _ = cause
        self.last_error = error_code
        self.state = DeviceState.ERROR
        self._emit_snapshot()
        return RuntimeError(error_code.value)

