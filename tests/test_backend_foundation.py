"""Tests for the MVP backend foundation service."""

import unittest

from backend_foundation.errors import ConflictError, NotFoundError
from backend_foundation.models import BindStatus, FailureCode, SessionState, StepStatus
from backend_foundation.service import BackendFoundationService


class BackendFoundationServiceTests(unittest.TestCase):
    def test_bind_device_sets_owner_and_entitlement_snapshot(self) -> None:
        service = BackendFoundationService()
        account = service.create_account(auth_subject="auth0|user-1", display_name="MVP User")
        device = service.register_device(
            device_id="device-001",
            hardware_model="pet-v1",
            firmware_version="1.0.0",
            pairing_code="PAIR-001",
        )

        binding = service.bind_device(account.account_id, "PAIR-001")
        entitlement = service.get_entitlement(account.account_id)
        devices = service.list_admin_devices(bind_status=BindStatus.BOUND)

        self.assertEqual(binding.account_id, account.account_id)
        self.assertEqual(binding.device_id, device.device_id)
        self.assertEqual(entitlement.account_id, account.account_id)
        self.assertTrue(entitlement.features["voiceSession"])
        self.assertEqual(devices[0].owner_account_id, account.account_id)

    def test_bind_device_rejects_already_bound_device(self) -> None:
        service = BackendFoundationService()
        first_account = service.create_account(auth_subject="auth0|user-1")
        second_account = service.create_account(auth_subject="auth0|user-2")
        service.register_device(
            device_id="device-001",
            hardware_model="pet-v1",
            firmware_version="1.0.0",
            pairing_code="PAIR-001",
        )
        service.bind_device(first_account.account_id, "PAIR-001")

        with self.assertRaises(ConflictError):
            service.bind_device(second_account.account_id, "PAIR-001")

    def test_session_lifecycle_and_admin_overview(self) -> None:
        service = BackendFoundationService()
        account = service.create_account(auth_subject="auth0|user-1")
        service.register_device(
            device_id="device-001",
            hardware_model="pet-v1",
            firmware_version="1.0.0",
            pairing_code="PAIR-001",
        )
        service.bind_device(account.account_id, "PAIR-001")

        session = service.start_session(
            account_id=account.account_id,
            device_id="device-001",
            firmware_version="1.0.0",
        )
        service.update_session(
            session.session_id,
            SessionState.REASONING,
            asr_status=StepStatus.SUCCEEDED,
            continuity_recall_used=True,
            notes="ASR finished and context loaded.",
        )
        completed = service.update_session(
            session.session_id,
            SessionState.COMPLETED,
            llm_status=StepStatus.SUCCEEDED,
            tts_status=StepStatus.SUCCEEDED,
            first_response_latency_ms=1800,
            notes="Response played successfully.",
        )
        overview = service.get_admin_overview()

        self.assertIs(completed.state, SessionState.COMPLETED)
        self.assertTrue(completed.continuity_recall_used)
        self.assertEqual(completed.first_response_latency_ms, 1800)
        self.assertEqual(len(completed.transitions), 3)
        self.assertEqual(overview.total_accounts, 1)
        self.assertEqual(overview.bound_devices, 1)
        self.assertEqual(overview.completed_sessions, 1)
        self.assertEqual(overview.failed_sessions, 0)

    def test_admin_session_filters_by_failure_code(self) -> None:
        service = BackendFoundationService()
        account = service.create_account(auth_subject="auth0|user-1")
        service.register_device(
            device_id="device-001",
            hardware_model="pet-v1",
            firmware_version="1.0.0",
            pairing_code="PAIR-001",
        )
        service.bind_device(account.account_id, "PAIR-001")
        session = service.start_session(
            account_id=account.account_id,
            device_id="device-001",
            firmware_version="1.0.0",
        )

        service.update_session(
            session.session_id,
            SessionState.FAILED,
            asr_status=StepStatus.FAILED,
            failure_code=FailureCode.ASR_FAILED,
            notes="ASR provider returned no transcript.",
        )

        failed_sessions = service.list_admin_sessions(failure_code=FailureCode.ASR_FAILED)

        self.assertEqual(len(failed_sessions), 1)
        self.assertIs(failed_sessions[0].failure_code, FailureCode.ASR_FAILED)
        self.assertIsNotNone(failed_sessions[0].ended_at)

    def test_update_session_can_clear_failure_code(self) -> None:
        service = BackendFoundationService()
        account = service.create_account(auth_subject="auth0|user-1")
        service.register_device(
            device_id="device-001",
            hardware_model="pet-v1",
            firmware_version="1.0.0",
            pairing_code="PAIR-001",
        )
        service.bind_device(account.account_id, "PAIR-001")
        session = service.start_session(
            account_id=account.account_id,
            device_id="device-001",
            firmware_version="1.0.0",
        )

        service.update_session(
            session.session_id,
            SessionState.FALLBACK,
            llm_status=StepStatus.FAILED,
            failure_code=FailureCode.LLM_FAILED,
            fallback_used=True,
            notes="First run fell back after llm failure.",
        )
        recovered = service.update_session(
            session.session_id,
            SessionState.COMPLETED,
            llm_status=StepStatus.SUCCEEDED,
            tts_status=StepStatus.SUCCEEDED,
            failure_code=None,
            fallback_used=False,
            notes="Second run completed successfully.",
        )

        self.assertIsNone(recovered.failure_code)
        self.assertIs(recovered.state, SessionState.COMPLETED)
        self.assertFalse(recovered.fallback_used)

    def test_unbind_requires_active_binding(self) -> None:
        service = BackendFoundationService()
        account = service.create_account(auth_subject="auth0|user-1")
        service.register_device(
            device_id="device-001",
            hardware_model="pet-v1",
            firmware_version="1.0.0",
            pairing_code="PAIR-001",
        )

        with self.assertRaises(NotFoundError):
            service.unbind_device(account.account_id, "device-001")


if __name__ == "__main__":
    unittest.main()
