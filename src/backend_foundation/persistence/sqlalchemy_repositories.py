"""SQLAlchemy repository implementations for the backend foundation."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import (
    Account,
    BindStatus,
    BindingRecord,
    Device,
    DeviceStatus,
    EntitlementTier,
    FailureCode,
    Session as DomainSession,
    SessionState,
    SessionTransition,
    StepStatus,
)
from ..repositories import (
    AccountRepository,
    BindingRepository,
    DeviceQuery,
    DeviceRepository,
    SessionQuery,
    SessionRepository,
)
from .orm_models import AccountORM, BindingRecordORM, DeviceORM, SessionORM, SessionTransitionORM


class SqlAlchemyAccountRepository(AccountRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, account: Account) -> None:
        self._db.add(_account_to_orm(account))
        self._db.flush()

    def save(self, account: Account) -> None:
        orm = self._db.get(AccountORM, account.account_id)
        if orm is None:
            self.add(account)
            return
        orm.auth_subject = account.auth_subject
        orm.display_name = account.display_name
        orm.default_role_id = account.default_role_id
        orm.entitlement_tier = account.entitlement_tier.value
        orm.created_at = account.created_at
        self._db.flush()

    def get(self, account_id: str) -> Account | None:
        orm = self._db.get(AccountORM, account_id)
        return _account_from_orm(orm) if orm else None

    def get_by_auth_subject(self, auth_subject: str) -> Account | None:
        orm = self._db.scalar(select(AccountORM).where(AccountORM.auth_subject == auth_subject))
        return _account_from_orm(orm) if orm else None

    def list_all(self) -> list[Account]:
        return [_account_from_orm(item) for item in self._db.scalars(select(AccountORM)).all()]


class SqlAlchemyDeviceRepository(DeviceRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, device: Device) -> None:
        self._db.add(_device_to_orm(device))
        self._db.flush()

    def save(self, device: Device) -> None:
        orm = self._db.get(DeviceORM, device.device_id)
        if orm is None:
            self.add(device)
            return
        orm.hardware_model = device.hardware_model
        orm.firmware_version = device.firmware_version
        orm.pairing_code = device.pairing_code
        orm.device_status = device.device_status.value
        orm.bind_status = device.bind_status.value
        orm.owner_account_id = device.owner_account_id
        orm.created_at = device.created_at
        orm.last_online_at = device.last_online_at
        self._db.flush()

    def get(self, device_id: str) -> Device | None:
        orm = self._db.get(DeviceORM, device_id)
        return _device_from_orm(orm) if orm else None

    def get_by_pairing_code(self, pairing_code: str) -> Device | None:
        orm = self._db.scalar(select(DeviceORM).where(DeviceORM.pairing_code == pairing_code))
        return _device_from_orm(orm) if orm else None

    def list(self, query: DeviceQuery | None = None) -> list[Device]:
        stmt = select(DeviceORM)
        if query is not None:
            if query.bind_status is not None:
                stmt = stmt.where(DeviceORM.bind_status == query.bind_status.value)
            if query.owner_account_id is not None:
                stmt = stmt.where(DeviceORM.owner_account_id == query.owner_account_id)
        return [_device_from_orm(item) for item in self._db.scalars(stmt).all()]

    def list_all(self) -> list[Device]:
        return self.list(None)


class SqlAlchemyBindingRepository(BindingRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, binding: BindingRecord) -> None:
        self._db.add(_binding_to_orm(binding))
        self._db.flush()

    def save(self, binding: BindingRecord) -> None:
        orm = self._db.get(BindingRecordORM, binding.binding_id)
        if orm is None:
            self.add(binding)
            return
        orm.account_id = binding.account_id
        orm.device_id = binding.device_id
        orm.status = binding.status.value
        orm.bound_at = binding.bound_at
        orm.unbound_at = binding.unbound_at
        self._db.flush()

    def get_active(self, device_id: str, account_id: str) -> BindingRecord | None:
        stmt = select(BindingRecordORM).where(
            BindingRecordORM.device_id == device_id,
            BindingRecordORM.account_id == account_id,
            BindingRecordORM.status == BindStatus.BOUND.value,
            BindingRecordORM.unbound_at.is_(None),
        )
        orm = self._db.scalar(stmt)
        return _binding_from_orm(orm) if orm else None

    def list_by_device(self, device_id: str) -> list[BindingRecord]:
        stmt = select(BindingRecordORM).where(BindingRecordORM.device_id == device_id)
        return [_binding_from_orm(item) for item in self._db.scalars(stmt).all()]

    def list_all(self) -> list[BindingRecord]:
        return [_binding_from_orm(item) for item in self._db.scalars(select(BindingRecordORM)).all()]


class SqlAlchemySessionRepository(SessionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, session: DomainSession) -> None:
        self._db.add(_session_to_orm(session))
        self._db.flush()

    def save(self, session: DomainSession) -> None:
        orm = self._db.scalar(
            select(SessionORM)
            .options(selectinload(SessionORM.transitions))
            .where(SessionORM.session_id == session.session_id)
        )
        if orm is None:
            self.add(session)
            return
        orm.account_id = session.account_id
        orm.device_id = session.device_id
        orm.role_id = session.role_id
        orm.entitlement_tier = session.entitlement_tier.value
        orm.state = session.state.value
        orm.asr_status = session.asr_status.value
        orm.llm_status = session.llm_status.value
        orm.tts_status = session.tts_status.value
        orm.safety_flag = session.safety_flag
        orm.fallback_used = session.fallback_used
        orm.continuity_recall_used = session.continuity_recall_used
        orm.first_response_latency_ms = session.first_response_latency_ms
        orm.failure_code = session.failure_code.value if session.failure_code else None
        orm.firmware_version = session.firmware_version
        orm.started_at = session.started_at
        orm.ended_at = session.ended_at
        orm.transitions = [
            SessionTransitionORM(
                transition_id=_new_transition_id(),
                session_id=session.session_id,
                state=transition.state.value,
                recorded_at=transition.recorded_at,
                notes=transition.notes,
            )
            for transition in session.transitions
        ]
        self._db.flush()

    def get(self, session_id: str) -> DomainSession | None:
        stmt = (
            select(SessionORM)
            .options(selectinload(SessionORM.transitions))
            .where(SessionORM.session_id == session_id)
        )
        orm = self._db.scalar(stmt)
        return _session_from_orm(orm) if orm else None

    def list(self, query: SessionQuery | None = None) -> list[DomainSession]:
        stmt = select(SessionORM).options(selectinload(SessionORM.transitions))
        if query is not None:
            if query.state is not None:
                stmt = stmt.where(SessionORM.state == query.state.value)
            if query.failure_code is not None:
                stmt = stmt.where(SessionORM.failure_code == query.failure_code.value)
            if query.account_id is not None:
                stmt = stmt.where(SessionORM.account_id == query.account_id)
            if query.device_id is not None:
                stmt = stmt.where(SessionORM.device_id == query.device_id)
        return [_session_from_orm(item) for item in self._db.scalars(stmt).all()]

    def list_all(self) -> list[DomainSession]:
        return self.list(None)


def _account_to_orm(account: Account) -> AccountORM:
    return AccountORM(
        account_id=account.account_id,
        auth_subject=account.auth_subject,
        display_name=account.display_name,
        default_role_id=account.default_role_id,
        entitlement_tier=account.entitlement_tier.value,
        created_at=account.created_at,
    )


def _account_from_orm(orm: AccountORM) -> Account:
    return Account(
        account_id=orm.account_id,
        auth_subject=orm.auth_subject,
        display_name=orm.display_name,
        default_role_id=orm.default_role_id,
        entitlement_tier=EntitlementTier(orm.entitlement_tier),
        created_at=orm.created_at,
    )


def _device_to_orm(device: Device) -> DeviceORM:
    return DeviceORM(
        device_id=device.device_id,
        hardware_model=device.hardware_model,
        firmware_version=device.firmware_version,
        pairing_code=device.pairing_code,
        device_status=device.device_status.value,
        bind_status=device.bind_status.value,
        owner_account_id=device.owner_account_id,
        created_at=device.created_at,
        last_online_at=device.last_online_at,
    )


def _device_from_orm(orm: DeviceORM) -> Device:
    return Device(
        device_id=orm.device_id,
        hardware_model=orm.hardware_model,
        firmware_version=orm.firmware_version,
        pairing_code=orm.pairing_code,
        device_status=DeviceStatus(orm.device_status),
        bind_status=BindStatus(orm.bind_status),
        owner_account_id=orm.owner_account_id,
        created_at=orm.created_at,
        last_online_at=orm.last_online_at,
    )


def _binding_to_orm(binding: BindingRecord) -> BindingRecordORM:
    return BindingRecordORM(
        binding_id=binding.binding_id,
        account_id=binding.account_id,
        device_id=binding.device_id,
        status=binding.status.value,
        bound_at=binding.bound_at,
        unbound_at=binding.unbound_at,
    )


def _binding_from_orm(orm: BindingRecordORM) -> BindingRecord:
    return BindingRecord(
        binding_id=orm.binding_id,
        account_id=orm.account_id,
        device_id=orm.device_id,
        status=BindStatus(orm.status),
        bound_at=orm.bound_at,
        unbound_at=orm.unbound_at,
    )


def _session_to_orm(session: DomainSession) -> SessionORM:
    return SessionORM(
        session_id=session.session_id,
        account_id=session.account_id,
        device_id=session.device_id,
        role_id=session.role_id,
        entitlement_tier=session.entitlement_tier.value,
        state=session.state.value,
        asr_status=session.asr_status.value,
        llm_status=session.llm_status.value,
        tts_status=session.tts_status.value,
        safety_flag=session.safety_flag,
        fallback_used=session.fallback_used,
        continuity_recall_used=session.continuity_recall_used,
        first_response_latency_ms=session.first_response_latency_ms,
        failure_code=session.failure_code.value if session.failure_code else None,
        firmware_version=session.firmware_version,
        started_at=session.started_at,
        ended_at=session.ended_at,
        transitions=[
            SessionTransitionORM(
                transition_id=_new_transition_id(),
                session_id=session.session_id,
                state=transition.state.value,
                recorded_at=transition.recorded_at,
                notes=transition.notes,
            )
            for transition in session.transitions
        ],
    )


def _session_from_orm(orm: SessionORM) -> DomainSession:
    return DomainSession(
        session_id=orm.session_id,
        account_id=orm.account_id,
        device_id=orm.device_id,
        role_id=orm.role_id,
        entitlement_tier=EntitlementTier(orm.entitlement_tier),
        state=SessionState(orm.state),
        asr_status=StepStatus(orm.asr_status),
        llm_status=StepStatus(orm.llm_status),
        tts_status=StepStatus(orm.tts_status),
        safety_flag=orm.safety_flag,
        fallback_used=orm.fallback_used,
        continuity_recall_used=orm.continuity_recall_used,
        firmware_version=orm.firmware_version,
        started_at=orm.started_at,
        ended_at=orm.ended_at,
        first_response_latency_ms=orm.first_response_latency_ms,
        failure_code=FailureCode(orm.failure_code) if orm.failure_code else None,
        transitions=[
            SessionTransition(
                state=SessionState(transition.state),
                recorded_at=transition.recorded_at,
                notes=transition.notes,
            )
            for transition in orm.transitions
        ],
    )


def _new_transition_id() -> str:
    return f"trn_{uuid4().hex[:12]}"
