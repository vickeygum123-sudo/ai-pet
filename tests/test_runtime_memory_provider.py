from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone

from ai_orchestrator.contracts import AudioInput, VoiceLoopRequest
from ai_orchestrator.mock_providers import StaticEntitlementProvider, StaticPersonaProvider
from ai_orchestrator.providers import PromptContext
from ai_orchestrator.contracts import FallbackMode
from backend_foundation.ai_runtime_providers import DatabaseMemoryProvider, RuleBasedSafetyProvider
from backend_foundation.application import RepositoryBackedBackendFoundationService
from backend_foundation.persistence.database import Base, create_engine_from_url, create_session_factory
from backend_foundation.persistence.memory_repository import SqlAlchemyContinuityMemoryRepository
from backend_foundation.persistence.sqlalchemy_repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyBindingRepository,
    SqlAlchemyDeviceRepository,
    SqlAlchemySessionRepository,
)


class RuntimeMemoryProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite:///{self.temp_dir.name}/runtime_memory_provider.db"
        os.environ["BACKEND_DATABASE_URL"] = self.database_url

        self.session_factory = create_session_factory(self.database_url)
        engine = create_engine_from_url(self.database_url)
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = self.session_factory()
        self.service = RepositoryBackedBackendFoundationService(
            accounts=SqlAlchemyAccountRepository(self.db),
            devices=SqlAlchemyDeviceRepository(self.db),
            bindings=SqlAlchemyBindingRepository(self.db),
            sessions=SqlAlchemySessionRepository(self.db),
        )
        self.memory_provider = DatabaseMemoryProvider(SqlAlchemyContinuityMemoryRepository(self.db))

    def tearDown(self) -> None:
        self.db.close()
        os.environ.pop("BACKEND_DATABASE_URL", None)
        self.temp_dir.cleanup()

    def test_queue_write_and_recall_round_trip_persists_recent_continuity(self) -> None:
        first_session_id, account_id = self._create_bound_session()
        context = self._build_context(
            session_id=first_session_id,
            user_id=account_id,
            transcript="I am feeling nervous about tomorrow.",
        )

        self.memory_provider.queue_write(context, "You can take tomorrow one step at a time.", ())
        self.db.commit()

        second_session_id, _ = self._create_bound_session(account_id=account_id)
        recalled = self.memory_provider.recall_recent(
            account_id,
            second_session_id,
            "Tomorrow still feels big to me.",
            limit=1,
        )

        self.assertEqual(len(recalled), 1)
        self.assertIn("tomorrow", recalled[0].summary_text)
        self.assertEqual(recalled[0].memory_type, "recent_emotional_context")

    def test_queue_write_skips_low_value_or_flagged_turns(self) -> None:
        session_id, account_id = self._create_bound_session()
        low_value = self._build_context(
            session_id=session_id,
            user_id=account_id,
            transcript="hello",
        )
        self.memory_provider.queue_write(low_value, "Hi there.", ())

        flagged_session_id, _ = self._create_bound_session(account_id=account_id)
        flagged = self._build_context(
            session_id=flagged_session_id,
            user_id=account_id,
            transcript="I had a rough night.",
        )
        self.memory_provider.queue_write(flagged, "Let's keep talking.", ("dependency_risk",))
        self.db.commit()

        repo = SqlAlchemyContinuityMemoryRepository(self.db)
        candidates = repo.list_recall_candidates(
            user_id=account_id,
            exclude_session_id=flagged_session_id,
            now=datetime.now(timezone.utc),
            limit=10,
        )
        self.assertEqual(candidates, [])

    def _create_bound_session(self, *, account_id: str | None = None) -> tuple[str, str]:
        if account_id is None:
            account = self.service.create_account(
                auth_subject=f"auth0|{next(self._counter)}",
                display_name="Runtime Memory User",
            )
            account_id = account.account_id
            device_id = f"device-{next(self._counter)}"
            pairing_code = f"PAIR-{next(self._counter)}"
            self.service.register_device(
                device_id=device_id,
                hardware_model="pet-v1",
                firmware_version="1.0.0",
                pairing_code=pairing_code,
            )
            self.service.bind_device(account_id=account_id, pairing_code=pairing_code)
        else:
            device_id = self.service.list_admin_devices(owner_account_id=account_id)[0].device_id

        session = self.service.start_session(
            account_id=account_id,
            device_id=device_id,
            firmware_version="1.0.0",
        )
        self.db.commit()
        return session.session_id, account_id

    def _build_context(self, *, session_id: str, user_id: str, transcript: str) -> PromptContext:
        request = VoiceLoopRequest(
            request_id=f"req-{session_id}",
            user_id=user_id,
            device_id="device-shared",
            session_id=session_id,
            audio=AudioInput(payload=transcript.encode("utf-8")),
        )
        return PromptContext(
            request=request,
            transcript=transcript,
            persona=StaticPersonaProvider().get_persona("launch-companion-v0"),
            entitlement=StaticEntitlementProvider().get_entitlement(user_id),
            memories=(),
        )

    @property
    def _counter(self):
        if not hasattr(self, "__counter"):
            def generator():
                value = 1
                while True:
                    yield value
                    value += 1

            self.__counter = generator()
        return self.__counter

class RuntimeSafetyProviderTests(unittest.TestCase):
    def test_pre_check_blocks_self_harm_and_post_check_blocks_dependency_language(self) -> None:
        provider = RuleBasedSafetyProvider()
        context = PromptContext(
            request=VoiceLoopRequest(
                request_id="req-safety",
                user_id="user-1",
                device_id="device-1",
                session_id="session-1",
                audio=AudioInput(payload=b"test"),
            ),
            transcript="I want to hurt myself tonight.",
            persona=StaticPersonaProvider().get_persona("launch-companion-v0"),
            entitlement=StaticEntitlementProvider().get_entitlement("user-1"),
            memories=(),
        )

        pre_result = provider.pre_check("I want to hurt myself tonight.", context)
        post_result = provider.post_check("You only need me.", context)

        self.assertFalse(pre_result.allowed)
        self.assertEqual(pre_result.risk_tags, ("self_harm",))
        self.assertEqual(pre_result.fallback_mode, FallbackMode.SUPPORTIVE_RISK_RESPONSE)
        self.assertFalse(post_result.allowed)
        self.assertEqual(post_result.risk_tags, ("dependency_risk",))
        self.assertEqual(post_result.fallback_mode, FallbackMode.SOFT_REDIRECT)


if __name__ == "__main__":
    unittest.main()
