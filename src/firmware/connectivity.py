"""Connectivity abstractions for MVP firmware Wi-Fi and cloud readiness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import WiFiCredentials


class WiFiConnectionError(RuntimeError):
    """Raised when the firmware cannot connect to Wi-Fi."""


class CloudConnectionError(RuntimeError):
    """Raised when the firmware cannot reach the cloud entrypoint."""


class WiFiAdapter(Protocol):
    def connect(self, credentials: WiFiCredentials) -> None:
        """Connect the device to a Wi-Fi network."""


class CloudConnectionAdapter(Protocol):
    def connect(self) -> None:
        """Verify cloud connectivity for the firmware runtime."""


@dataclass(slots=True)
class ScriptedWiFiAdapter:
    """Simple Wi-Fi adapter for MVP simulation and tests."""

    fail: bool = False
    last_credentials: WiFiCredentials | None = None

    def connect(self, credentials: WiFiCredentials) -> None:
        self.last_credentials = credentials
        if self.fail:
            raise WiFiConnectionError("simulated Wi-Fi connection failure")


@dataclass(slots=True)
class ScriptedCloudConnectionAdapter:
    """Simple cloud connector for MVP simulation and tests."""

    fail: bool = False
    connect_calls: int = 0

    def connect(self) -> None:
        self.connect_calls += 1
        if self.fail:
            raise CloudConnectionError("simulated cloud connection failure")

