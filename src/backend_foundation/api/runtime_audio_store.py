"""Small in-memory store for voice-loop audio artifacts during local runtime."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(slots=True)
class AudioArtifact:
    audio_bytes: bytes
    audio_format: str


class VoiceLoopAudioStore:
    def __init__(self, *, max_entries: int = 16) -> None:
        self._max_entries = max_entries
        self._items: OrderedDict[str, AudioArtifact] = OrderedDict()

    def put(self, *, session_id: str, request_id: str, audio_bytes: bytes, audio_format: str) -> str:
        key = self._build_key(session_id=session_id, request_id=request_id)
        self._items[key] = AudioArtifact(audio_bytes=audio_bytes, audio_format=audio_format)
        self._items.move_to_end(key)
        while len(self._items) > self._max_entries:
            self._items.popitem(last=False)
        return key

    def get(self, *, session_id: str, request_id: str) -> AudioArtifact | None:
        key = self._build_key(session_id=session_id, request_id=request_id)
        artifact = self._items.get(key)
        if artifact is not None:
            self._items.move_to_end(key)
        return artifact

    @staticmethod
    def _build_key(*, session_id: str, request_id: str) -> str:
        return f"{session_id}:{request_id}"
