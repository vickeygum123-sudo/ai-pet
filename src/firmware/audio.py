"""Audio capture and playback abstractions for the MVP firmware simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .models import AudioFrame


class AudioCaptureError(RuntimeError):
    """Raised when the simulated microphone cannot capture audio."""


class AudioPlaybackError(RuntimeError):
    """Raised when the simulated speaker cannot play audio."""


class AudioInput(Protocol):
    def capture(self) -> AudioFrame:
        """Return a single captured audio frame."""


class AudioOutput(Protocol):
    def play(self, frame: AudioFrame) -> None:
        """Play a single synthesized audio frame."""


@dataclass(slots=True)
class MemoryAudioInput:
    """Returns scripted audio frames for deterministic tests and local simulation."""

    frames: list[AudioFrame] = field(default_factory=list)
    fail: bool = False

    def capture(self) -> AudioFrame:
        if self.fail:
            raise AudioCaptureError("simulated audio capture failure")
        if not self.frames:
            raise AudioCaptureError("no scripted audio frames available")
        return self.frames.pop(0)


@dataclass(slots=True)
class MemoryAudioOutput:
    """Records played frames so tests can assert firmware playback behavior."""

    played_frames: list[AudioFrame] = field(default_factory=list)
    fail: bool = False

    def play(self, frame: AudioFrame) -> None:
        if self.fail:
            raise AudioPlaybackError("simulated audio playback failure")
        self.played_frames.append(frame)

