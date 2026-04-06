from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from backend_foundation.api.app import create_app
from backend_foundation.persistence.database import Base, create_engine_from_url


class BackendFoundationAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite:///{self.temp_dir.name}/backend_api_test.db"
        os.environ["BACKEND_DATABASE_URL"] = self.database_url

        from backend_foundation.api import dependencies

        dependencies.SessionLocal = dependencies.create_session_factory(self.database_url)
        engine = create_engine_from_url(self.database_url)
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        os.environ.pop("BACKEND_DATABASE_URL", None)
        self.temp_dir.cleanup()

    def test_bind_session_and_admin_flow(self) -> None:
        account = self.client.post(
            "/v1/accounts",
            json={"authSubject": "auth0|api-user", "displayName": "API User"},
        )
        self.assertEqual(account.status_code, 201)
        account_id = account.json()["accountId"]

        device = self.client.post(
            "/v1/internal/devices",
            json={
                "deviceId": "device-api-001",
                "hardwareModel": "pet-v1",
                "firmwareVersion": "1.0.0",
                "pairingCode": "PAIR-API-001",
            },
        )
        self.assertEqual(device.status_code, 201)

        binding = self.client.post(
            "/v1/device-bindings",
            json={"pairingCode": "PAIR-API-001"},
            headers={"X-Account-Id": account_id},
        )
        self.assertEqual(binding.status_code, 201)
        self.assertEqual(binding.json()["accountId"], account_id)

        entitlement = self.client.get("/v1/entitlements/me", headers={"X-Account-Id": account_id})
        self.assertEqual(entitlement.status_code, 200)
        self.assertTrue(entitlement.json()["features"]["voiceSession"])

        session = self.client.post(
            "/v1/device-sessions",
            json={
                "accountId": account_id,
                "deviceId": "device-api-001",
                "firmwareVersion": "1.0.0",
            },
        )
        self.assertEqual(session.status_code, 201)
        session_id = session.json()["sessionId"]

        updated = self.client.patch(
            f"/v1/device-sessions/{session_id}",
            json={
                "state": "completed",
                "asrStatus": "succeeded",
                "llmStatus": "succeeded",
                "ttsStatus": "succeeded",
                "firstResponseLatencyMs": 1700,
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["state"], "completed")

        overview = self.client.get("/v1/admin/overview")
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.json()["totalAccounts"], 1)
        self.assertEqual(overview.json()["completedSessions"], 1)

        sessions = self.client.get("/v1/admin/sessions", params={"state": "completed"})
        self.assertEqual(sessions.status_code, 200)
        self.assertEqual(len(sessions.json()["items"]), 1)

    def test_missing_auth_header_uses_stable_error_shape(self) -> None:
        response = self.client.get("/v1/accounts/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "code": "AUTH_HEADER_REQUIRED",
                "message": "Missing X-Account-Id header for MVP auth placeholder.",
            },
        )

    def test_invalid_pairing_code_returns_bind_specific_error(self) -> None:
        account = self.client.post(
            "/v1/accounts",
            json={"authSubject": "auth0|api-user-2", "displayName": "API User 2"},
        )
        account_id = account.json()["accountId"]

        response = self.client.post(
            "/v1/device-bindings",
            json={"pairingCode": "PAIR-UNKNOWN"},
            headers={"X-Account-Id": account_id},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "BIND_TARGET_UNAVAILABLE")

    def test_validation_error_uses_stable_error_shape(self) -> None:
        response = self.client.post("/v1/accounts", json={})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "VALIDATION_ERROR")


if __name__ == "__main__":
    unittest.main()
