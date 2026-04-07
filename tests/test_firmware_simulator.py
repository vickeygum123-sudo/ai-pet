from __future__ import annotations

import os
import tempfile
import unittest
from typing import Any
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from ai_orchestrator.config import OrchestratorConfig
from ai_orchestrator.mock_providers import (
    EchoASRProvider,
    InMemoryMemoryProvider,
    KeywordSafetyProvider,
    SimpleLLMProvider,
    SimpleTTSProvider,
    StaticEntitlementProvider,
    StaticPersonaProvider,
)
from ai_orchestrator.orchestrator import VoiceLoopOrchestrator
from backend_foundation.api.app import VOICE_LOOP_AUDIO_MODE_ENV, VOICE_LOOP_AUDIO_MODE_URL
from backend_foundation.api.app import create_app
from backend_foundation.persistence.database import Base, create_engine_from_url
from firmware.audio import MemoryAudioInput, MemoryAudioOutput
from firmware.cloud import BackendVoiceLoopGateway, CloudRequestError
from firmware.connectivity import ScriptedCloudConnectionAdapter, ScriptedWiFiAdapter
from firmware.device import FirmwareDevice, InMemoryDeviceStatusReporter
from firmware.models import AudioFrame, DeviceState, VoiceTurnRequest, WiFiCredentials


class TestClientJSONTransport:
    def __init__(self, client: TestClient) -> None:
        self._client = client

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_path(path)
        if path == "/__connectivity_probe__":
            return {"ok": True}

        response = self._client.post(path, json=payload)
        if response.status_code >= 400:
            raise CloudRequestError(f"status={response.status_code}")
        return response.json()

    def get_bytes(self, path: str) -> tuple[bytes, str | None]:
        path = self._resolve_path(path)
        response = self._client.get(path)
        if response.status_code >= 400:
            raise CloudRequestError(f"status={response.status_code}")
        return response.content, response.headers.get("content-type")

    @staticmethod
    def _resolve_path(path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            split = urlsplit(path)
            return split.path + (f"?{split.query}" if split.query else "")
        return path


class FirmwareSimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite:///{self.temp_dir.name}/firmware_simulator_test.db"
        os.environ["BACKEND_DATABASE_URL"] = self.database_url

        from backend_foundation.api import dependencies

        dependencies.SessionLocal = dependencies.create_session_factory(self.database_url)
        engine = create_engine_from_url(self.database_url)
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        self.dependencies = dependencies
        self.app = create_app()
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        os.environ.pop("BACKEND_DATABASE_URL", None)
        os.environ.pop(VOICE_LOOP_AUDIO_MODE_ENV, None)
        self.temp_dir.cleanup()

    def make_orchestrator(self, *, tts: SimpleTTSProvider | None = None) -> VoiceLoopOrchestrator:
        return VoiceLoopOrchestrator(
            config=OrchestratorConfig(),
            asr=EchoASRProvider(),
            persona=StaticPersonaProvider(),
            entitlement=StaticEntitlementProvider(),
            memory=InMemoryMemoryProvider(),
            safety=KeywordSafetyProvider(),
            llm=SimpleLLMProvider(),
            tts=tts or SimpleTTSProvider(),
        )

    def override_orchestrator(self, orchestrator: VoiceLoopOrchestrator) -> None:
        self.app.dependency_overrides[self.dependencies.get_voice_loop_orchestrator] = lambda: orchestrator

    def create_session(self) -> str:
        account = self.client.post(
            "/v1/accounts",
            json={"authSubject": "auth0|firmware-user", "displayName": "Firmware User"},
        )
        account_id = account.json()["accountId"]

        self.client.post(
            "/v1/internal/devices",
            json={
                "deviceId": "device-fw-001",
                "hardwareModel": "pet-v1",
                "firmwareVersion": "0.1.0",
                "pairingCode": "PAIR-FW-001",
            },
        )
        self.client.post(
            "/v1/device-bindings",
            json={"pairingCode": "PAIR-FW-001"},
            headers={"X-Account-Id": account_id},
        )
        session = self.client.post(
            "/v1/device-sessions",
            json={
                "accountId": account_id,
                "deviceId": "device-fw-001",
                "firmwareVersion": "0.1.0",
            },
        )
        return session.json()["sessionId"]

    def make_device(
        self,
        *,
        audio_input: MemoryAudioInput | None = None,
        audio_output: MemoryAudioOutput | None = None,
        cloud_connection: ScriptedCloudConnectionAdapter | None = None,
    ) -> tuple[FirmwareDevice, InMemoryDeviceStatusReporter]:
        reporter = InMemoryDeviceStatusReporter()
        device = FirmwareDevice(
            device_id="device-fw-001",
            wifi_adapter=ScriptedWiFiAdapter(),
            cloud_connection=cloud_connection or ScriptedCloudConnectionAdapter(),
            audio_input=audio_input
            or MemoryAudioInput(
                frames=[AudioFrame(payload=b"I am glad we can talk again.", duration_ms=900)]
            ),
            audio_output=audio_output or MemoryAudioOutput(),
            voice_gateway=BackendVoiceLoopGateway(TestClientJSONTransport(self.client)),
            status_reporter=reporter,
        )
        return device, reporter

    def test_boot_wifi_and_cloud_flow_reaches_ready_to_speak(self) -> None:
        device, reporter = self.make_device()

        device.boot()
        device.provision_wifi(WiFiCredentials(ssid="demo-wifi", password="secret-pass"))
        snapshot = device.connect_cloud()

        self.assertEqual(snapshot.state, DeviceState.READY_TO_SPEAK)
        self.assertTrue(snapshot.wifi_connected)
        self.assertTrue(snapshot.cloud_connected)
        self.assertEqual(
            [item.state for item in reporter.snapshots],
            [
                DeviceState.BOOTING,
                DeviceState.PAIRING_READY,
                DeviceState.CONNECTING_WIFI,
                DeviceState.WIFI_CONNECTED,
                DeviceState.CONNECTING_CLOUD,
                DeviceState.READY_TO_SPEAK,
            ],
        )

    def test_successful_voice_turn_plays_returned_audio_and_recovers_to_ready(self) -> None:
        self.override_orchestrator(self.make_orchestrator())
        session_id = self.create_session()
        audio_output = MemoryAudioOutput()
        device, reporter = self.make_device(audio_output=audio_output)

        device.boot()
        device.provision_wifi(WiFiCredentials(ssid="demo-wifi", password="secret-pass"))
        device.connect_cloud()

        response = device.run_voice_turn(
            VoiceTurnRequest(session_id=session_id, request_id="req-fw-001", locale="en-US")
        )

        self.assertEqual(response.session_state, "completed")
        self.assertEqual(device.state, DeviceState.READY_TO_SPEAK)
        self.assertEqual(len(audio_output.played_frames), 1)
        self.assertIn("I am here with you", audio_output.played_frames[0].payload.decode("utf-8"))
        self.assertEqual(
            [item.state for item in reporter.snapshots[-4:]],
            [
                DeviceState.LISTENING,
                DeviceState.THINKING,
                DeviceState.SPEAKING,
                DeviceState.READY_TO_SPEAK,
            ],
        )

    def test_successful_voice_turn_can_download_audio_via_url(self) -> None:
        os.environ[VOICE_LOOP_AUDIO_MODE_ENV] = VOICE_LOOP_AUDIO_MODE_URL
        self.override_orchestrator(self.make_orchestrator())
        session_id = self.create_session()
        audio_output = MemoryAudioOutput()
        device, reporter = self.make_device(audio_output=audio_output)

        device.boot()
        device.provision_wifi(WiFiCredentials(ssid="demo-wifi", password="secret-pass"))
        device.connect_cloud()

        response = device.run_voice_turn(
            VoiceTurnRequest(session_id=session_id, request_id="req-fw-url-001", locale="en-US")
        )

        self.assertEqual(response.session_state, "completed")
        self.assertTrue(response.audio_url)
        self.assertEqual(device.state, DeviceState.READY_TO_SPEAK)
        self.assertEqual(len(audio_output.played_frames), 1)
        self.assertIn("I am here with you", audio_output.played_frames[0].payload.decode("utf-8"))
        self.assertEqual(
            [item.state for item in reporter.snapshots[-4:]],
            [
                DeviceState.LISTENING,
                DeviceState.THINKING,
                DeviceState.SPEAKING,
                DeviceState.READY_TO_SPEAK,
            ],
        )

    def test_tts_failure_moves_device_into_error_state(self) -> None:
        self.override_orchestrator(self.make_orchestrator(tts=SimpleTTSProvider(fail=True)))
        session_id = self.create_session()
        device, _ = self.make_device()

        device.boot()
        device.provision_wifi(WiFiCredentials(ssid="demo-wifi", password="secret-pass"))
        device.connect_cloud()

        with self.assertRaisesRegex(RuntimeError, "cloud_audio_missing"):
            device.run_voice_turn(
                VoiceTurnRequest(session_id=session_id, request_id="req-fw-002", locale="en-US")
            )

        self.assertEqual(device.state, DeviceState.ERROR)


if __name__ == "__main__":
    unittest.main()
