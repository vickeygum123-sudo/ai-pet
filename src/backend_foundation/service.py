"""In-memory backend foundation service for MVP contracts and rule validation."""

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

_UNSET = object()


class BackendFoundationService:
    """Framework-neutral service layer for the backend MVP foundation."""

    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}
        self._devices: dict[str, Device] = {}
        self._bindings: dict[str, BindingRecord] = {}
        self._sessions: dict[str, Session] = {}

    def create_account(
        self,
        auth_subject: str,
        display_name: str | None = None,
        default_role_id: str = "launch-companion-v0",
        entitlement_tier: EntitlementTier = EntitlementTier.FREE,
        created_at: datetime | None = None,
    ) -> Account:
        account = Account(
            account_id=self._new_id("acct"),
            auth_subject=auth_subject,
            display_name=display_name,
            default_role_id=default_role_id,
            entitlement_tier=entitlement_tier,
            created_at=created_at or self._now(),
        )
        self._accounts[account.account_id] = account
        return account

    def register_device(
        self,
        device_id: str,
        hardware_model: str,
        firmware_version: str,
        pairing_code: str,
        created_at: datetime | None = None,
    ) -> Device:
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
        self._devices[device.device_id] = device
        return device

    def bind_device(
        self,
        account_id: str,
        pairing_code: str,
        bound_at: datetime | None = None,
    ) -> BindingRecord:
        self._require_account(account_id)
        device = self._find_device_by_pairing_code(pairing_code)
        if device.bind_status is BindStatus.BOUND:
            raise ConflictError(f"Device {device.device_id} is already bound.")

        device.bind_status = BindStatus.BOUND
        device.owner_account_id = account_id
        device.device_status = DeviceStatus.CONNECTED
        binding = BindingRecord(
            binding_id=self._new_id("bind"),
            account_id=account_id,
            device_id=device.device_id,
            status=BindStatus.BOUND,
            bound_at=bound_at or self._now(),
        )
        self._bindings[binding.binding_id] = binding
        return binding

    def unbind_device(
        self,
        account_id: str,
        device_id: str,
        unbound_at: datetime | None = None,
    ) -> BindingRecord:
        self._require_account(account_id)
        device = self._require_device(device_id)
        if device.owner_account_id != account_id or device.bind_status is not BindStatus.BOUND:
            raise NotFoundError(f"Device {device_id} has no active binding for account {account_id}.")

        binding = self._find_active_binding(device_id, account_id)
        binding.status = BindStatus.UNBOUND
        binding.unbound_at = unbound_at or self._now()
        device.bind_status = BindStatus.UNBOUND
        device.owner_account_id = None
        device.device_status = DeviceStatus.PAIRING_READY
        return binding

    def record_device_heartbeat(
        self,
        device_id: str,
        observed_at: datetime | None = None,
        firmware_version: str | None = None,
        device_status: DeviceStatus = DeviceStatus.READY_TO_SPEAK,
    ) -> Device:
        device = self._require_device(device_id)
        device.last_online_at = observed_at or self._now()
        device.device_status = device_status
        if firmware_version:
            device.firmware_version = firmware_version
        return device

    def get_entitlement(self, account_id: str) -> EntitlementSnapshot:
        account = self._require_account(account_id)
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
        account = self._require_account(account_id)
        device = self._require_device(device_id)
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
        self._sessions[session.session_id] = session
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
        session.transitions.append(
            SessionTransition(state=state, recorded_at=timestamp, notes=notes)
        )
        return session

    def get_admin_overview(self) -> AdminOverview:
        active_states = {
            SessionState.LISTENING,
            SessionState.TRANSCRIBING,
            SessionState.REASONING,
            SessionState.SYNTHESIZING,
            SessionState.SPEAKING,
        }
        return AdminOverview(
            total_accounts=len(self._accounts),
            total_devices=len(self._devices),
            bound_devices=sum(1 for device in self._devices.values() if device.bind_status is BindStatus.BOUND),
            active_sessions=sum(1 for session in self._sessions.values() if session.state in active_states),
            completed_sessions=sum(1 for session in self._sessions.values() if session.state is SessionState.COMPLETED),
            failed_sessions=sum(1 for session in self._sessions.values() if session.state is SessionState.FAILED),
        )

    def list_admin_devices(
        self,
        *,
        bind_status: BindStatus | None = None,
        owner_account_id: str | None = None,
    ) -> list[Device]:
        devices = list(self._devices.values())
        if bind_status is not None:
            devices = [device for device in devices if device.bind_status is bind_status]
        if owner_account_id is not None:
            devices = [device for device in devices if device.owner_account_id == owner_account_id]
        return devices

    def list_admin_sessions(
        self,
        *,
        state: SessionState | None = None,
        failure_code: FailureCode | None = None,
        account_id: str | None = None,
        device_id: str | None = None,
    ) -> list[Session]:
        sessions = list(self._sessions.values())
        if state is not None:
            sessions = [session for session in sessions if session.state is state]
        if failure_code is not None:
            sessions = [session for session in sessions if session.failure_code is failure_code]
        if account_id is not None:
            sessions = [session for session in sessions if session.account_id == account_id]
        if device_id is not None:
            sessions = [session for session in sessions if session.device_id == device_id]
        return sessions

    def get_admin_session_detail(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise NotFoundError(f"Session {session_id} was not found.") from exc

    def _find_active_binding(self, device_id: str, account_id: str) -> BindingRecord:
        for binding in self._bindings.values():
            if (
                binding.device_id == device_id
                and binding.account_id == account_id
                and binding.status is BindStatus.BOUND
                and binding.unbound_at is None
            ):
                return binding
        raise NotFoundError(f"No active binding found for device {device_id} and account {account_id}.")

    def _find_device_by_pairing_code(self, pairing_code: str) -> Device:
        for device in self._devices.values():
            if device.pairing_code == pairing_code:
                return device
        raise NotFoundError(f"Pairing code {pairing_code} was not found.")

    def _require_account(self, account_id: str) -> Account:
        try:
            return self._accounts[account_id]
        except KeyError as exc:
            raise NotFoundError(f"Account {account_id} was not found.") from exc

    def _require_device(self, device_id: str) -> Device:
        try:
            return self._devices[device_id]
        except KeyError as exc:
            raise NotFoundError(f"Device {device_id} was not found.") from exc

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
