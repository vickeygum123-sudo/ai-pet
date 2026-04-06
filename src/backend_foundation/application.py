"""Repository-backed backend foundation service."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .errors import ConflictError, NotFoundError
from .models import (
    Account,
    AdminOverview,
    BindStatus,
    BindingRecord,
    Device,
    DeviceStatus,
    EntitlementSnapshot,
    EntitlementTier,
    FailureCode,
    Session,
    SessionState,
    SessionTransition,
    StepStatus,
)
from .repositories import (
    AccountRepository,
    BindingRepository,
    DeviceQuery,
    DeviceRepository,
    SessionQuery,
    SessionRepository,
)

_UNSET = object()


class RepositoryBackedBackendFoundationService:
    """Application service using repository interfaces and persistent storage."""

    def __init__(
        self,
        *,
        accounts: AccountRepository,
        devices: DeviceRepository,
        bindings: BindingRepository,
        sessions: SessionRepository,
    ) -> None:
        self._accounts = accounts
        self._devices = devices
        self._bindings = bindings
        self._sessions = sessions

    def create_account(
        self,
        auth_subject: str,
        display_name: str | None = None,
        default_role_id: str = "launch-companion-v0",
        entitlement_tier: EntitlementTier = EntitlementTier.FREE,
        created_at: datetime | None = None,
    ) -> Account:
        if self._accounts.get_by_auth_subject(auth_subject) is not None:
            raise ConflictError(f"Auth subject {auth_subject} already exists.")
        account = Account(
            account_id=self._new_id("acct"),
            auth_subject=auth_subject,
            display_name=display_name,
            default_role_id=default_role_id,
            entitlement_tier=entitlement_tier,
            created_at=created_at or self._now(),
        )
        self._accounts.add(account)
        return account

    def get_account(self, account_id: str) -> Account:
        account = self._accounts.get(account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} was not found.")
        return account

    def register_device(
        self,
        device_id: str,
        hardware_model: str,
        firmware_version: str,
        pairing_code: str,
        created_at: datetime | None = None,
    ) -> Device:
        if self._devices.get(device_id) is not None:
            raise ConflictError(f"Device {device_id} already exists.")
        if self._devices.get_by_pairing_code(pairing_code) is not None:
            raise ConflictError(f"Pairing code {pairing_code} is already active.")
        device = Device(
            device_id=device_id,
            hardware_model=hardware_model,
            firmware_version=firmware_version,
            pairing_code=pairing_code,
            device_status=DeviceStatus.PAIRING_READY,
            bind_status=BindStatus.UNBOUND,
            owner_account_id=None,
            created_at=created_at or self._now(),
        )
        self._devices.add(device)
        return device

    def bind_device(
        self,
        account_id: str,
        pairing_code: str,
        bound_at: datetime | None = None,
    ) -> BindingRecord:
        self.get_account(account_id)
        device = self._devices.get_by_pairing_code(pairing_code)
        if device is None:
            raise NotFoundError(f"Pairing code {pairing_code} was not found.")
        if device.bind_status is BindStatus.BOUND:
            raise ConflictError(f"Device {device.device_id} is already bound.")

        device.bind_status = BindStatus.BOUND
        device.owner_account_id = account_id
        device.device_status = DeviceStatus.CONNECTED
        self._devices.save(device)

        binding = BindingRecord(
            binding_id=self._new_id("bind"),
            account_id=account_id,
            device_id=device.device_id,
            status=BindStatus.BOUND,
            bound_at=bound_at or self._now(),
        )
        self._bindings.add(binding)
        return binding

    def unbind_device(
        self,
        account_id: str,
        device_id: str,
        unbound_at: datetime | None = None,
    ) -> BindingRecord:
        self.get_account(account_id)
        device = self._devices.get(device_id)
        if device is None:
            raise NotFoundError(f"Device {device_id} was not found.")
        if device.owner_account_id != account_id or device.bind_status is not BindStatus.BOUND:
            raise NotFoundError(f"Device {device_id} has no active binding for account {account_id}.")

        binding = self._bindings.get_active(device_id, account_id)
        if binding is None:
            raise NotFoundError(f"No active binding found for device {device_id} and account {account_id}.")
        binding.status = BindStatus.UNBOUND
        binding.unbound_at = unbound_at or self._now()
        self._bindings.save(binding)

        device.bind_status = BindStatus.UNBOUND
        device.owner_account_id = None
        device.device_status = DeviceStatus.PAIRING_READY
        self._devices.save(device)
        return binding

    def get_entitlement(self, account_id: str) -> EntitlementSnapshot:
        account = self.get_account(account_id)
        return EntitlementSnapshot(
            account_id=account.account_id,
            tier=account.entitlement_tier,
            features={
                "voiceSession": True,
                "recentContinuityMemory": True,
                "priorityGeneration": account.entitlement_tier is EntitlementTier.SUBSCRIBED,
            },
        )

    def start_session(
        self,
        account_id: str,
        device_id: str,
        firmware_version: str,
        role_id: str | None = None,
        started_at: datetime | None = None,
    ) -> Session:
        account = self.get_account(account_id)
        device = self._devices.get(device_id)
        if device is None:
            raise NotFoundError(f"Device {device_id} was not found.")
        if device.owner_account_id != account_id or device.bind_status is not BindStatus.BOUND:
            raise ConflictError(f"Device {device_id} is not actively bound to account {account_id}.")

        transition = SessionTransition(
            state=SessionState.LISTENING,
            recorded_at=started_at or self._now(),
            notes="Session opened by device gateway.",
        )
        session = Session(
            session_id=self._new_id("sess"),
            account_id=account.account_id,
            device_id=device.device_id,
            role_id=role_id or account.default_role_id,
            entitlement_tier=account.entitlement_tier,
            state=SessionState.LISTENING,
            asr_status=StepStatus.PENDING,
            llm_status=StepStatus.PENDING,
            tts_status=StepStatus.PENDING,
            safety_flag=False,
            fallback_used=False,
            continuity_recall_used=False,
            firmware_version=firmware_version,
            started_at=transition.recorded_at,
            transitions=[transition],
        )
        self._sessions.add(session)
        return session

    def update_session(
        self,
        session_id: str,
        state: SessionState,
        *,
        asr_status: StepStatus | None = None,
        llm_status: StepStatus | None = None,
        tts_status: StepStatus | None = None,
        safety_flag: bool | None = None,
        fallback_used: bool | None = None,
        continuity_recall_used: bool | None = None,
        first_response_latency_ms: int | None = None,
        failure_code: FailureCode | None | object = _UNSET,
        notes: str | None = None,
        recorded_at: datetime | None = None,
    ) -> Session:
        session = self.get_admin_session_detail(session_id)
        session.state = state
        if asr_status is not None:
            session.asr_status = asr_status
        if llm_status is not None:
            session.llm_status = llm_status
        if tts_status is not None:
            session.tts_status = tts_status
        if safety_flag is not None:
            session.safety_flag = safety_flag
        if fallback_used is not None:
            session.fallback_used = fallback_used
        if continuity_recall_used is not None:
            session.continuity_recall_used = continuity_recall_used
        if first_response_latency_ms is not None:
            session.first_response_latency_ms = first_response_latency_ms
        if failure_code is not _UNSET:
            session.failure_code = failure_code
        timestamp = recorded_at or self._now()
        if state in (SessionState.COMPLETED, SessionState.FAILED, SessionState.FALLBACK):
            session.ended_at = timestamp
        session.transitions.append(SessionTransition(state=state, recorded_at=timestamp, notes=notes))
        self._sessions.save(session)
        return session

    def get_admin_overview(self) -> AdminOverview:
        devices = self._devices.list_all()
        sessions = self._sessions.list_all()
        active_states = {
            SessionState.LISTENING,
            SessionState.TRANSCRIBING,
            SessionState.REASONING,
            SessionState.SYNTHESIZING,
            SessionState.SPEAKING,
        }
        return AdminOverview(
            total_accounts=len(self._accounts.list_all()),
            total_devices=len(devices),
            bound_devices=sum(1 for device in devices if device.bind_status is BindStatus.BOUND),
            active_sessions=sum(1 for session in sessions if session.state in active_states),
            completed_sessions=sum(1 for session in sessions if session.state is SessionState.COMPLETED),
            failed_sessions=sum(1 for session in sessions if session.state is SessionState.FAILED),
        )

    def list_admin_devices(
        self,
        *,
        bind_status: BindStatus | None = None,
        owner_account_id: str | None = None,
    ) -> list[Device]:
        return self._devices.list(DeviceQuery(bind_status=bind_status, owner_account_id=owner_account_id))

    def list_admin_sessions(
        self,
        *,
        state: SessionState | None = None,
        failure_code: FailureCode | None = None,
        account_id: str | None = None,
        device_id: str | None = None,
    ) -> list[Session]:
        return self._sessions.list(
            SessionQuery(
                state=state,
                failure_code=failure_code,
                account_id=account_id,
                device_id=device_id,
            )
        )

    def get_admin_session_detail(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFoundError(f"Session {session_id} was not found.")
        return session

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
