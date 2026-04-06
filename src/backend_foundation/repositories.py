"""Framework-neutral repository interfaces for the MVP backend foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import (
    Account,
    BindStatus,
    BindingRecord,
    Device,
    FailureCode,
    Session,
    SessionState,
)


@dataclass(slots=True)
class DeviceQuery:
    bind_status: BindStatus | None = None
    owner_account_id: str | None = None


@dataclass(slots=True)
class SessionQuery:
    state: SessionState | None = None
    failure_code: FailureCode | None = None
    account_id: str | None = None
    device_id: str | None = None


class AccountRepository(Protocol):
    def add(self, account: Account) -> None: ...

    def save(self, account: Account) -> None: ...

    def get(self, account_id: str) -> Account | None: ...

    def get_by_auth_subject(self, auth_subject: str) -> Account | None: ...

    def list_all(self) -> list[Account]: ...


class DeviceRepository(Protocol):
    def add(self, device: Device) -> None: ...

    def save(self, device: Device) -> None: ...

    def get(self, device_id: str) -> Device | None: ...

    def get_by_pairing_code(self, pairing_code: str) -> Device | None: ...

    def list(self, query: DeviceQuery | None = None) -> list[Device]: ...

    def list_all(self) -> list[Device]: ...


class BindingRepository(Protocol):
    def add(self, binding: BindingRecord) -> None: ...

    def save(self, binding: BindingRecord) -> None: ...

    def get_active(self, device_id: str, account_id: str) -> BindingRecord | None: ...

    def list_by_device(self, device_id: str) -> list[BindingRecord]: ...

    def list_all(self) -> list[BindingRecord]: ...


class SessionRepository(Protocol):
    def add(self, session: Session) -> None: ...

    def save(self, session: Session) -> None: ...

    def get(self, session_id: str) -> Session | None: ...

    def list(self, query: SessionQuery | None = None) -> list[Session]: ...

    def list_all(self) -> list[Session]: ...
