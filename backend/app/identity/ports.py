"""Framework-free storage contract for centrally revocable human identities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.app.identity.policy import HumanAccount, SessionFamily


@dataclass(frozen=True)
class AccountCredentials:
    account: HumanAccount
    login: str
    password_hash: str


@dataclass(frozen=True)
class SessionSecrets:
    family: SessionFamily
    access_sha256: str
    refresh_sha256: str
    csrf_sha256: str


@dataclass(frozen=True)
class ConsumedRefresh:
    family_id: UUID
    csrf_sha256: str
    expires_at: datetime


class IdentityRepository(Protocol):
    def account_by_login(self, login: str) -> AccountCredentials | None: ...
    def account(self, account_id: UUID, *, lock: bool = False) -> AccountCredentials | None: ...
    def add_account(self, account: AccountCredentials, now: datetime) -> None: ...
    def update_account(self, account: AccountCredentials, now: datetime) -> None: ...
    def reserve_login(self, login: str, now: datetime) -> bool: ...
    def prune_expired(self, now: datetime) -> None: ...
    def add_session(self, state: SessionSecrets) -> None: ...
    def access(self, digest: str) -> SessionSecrets | None: ...
    def refresh(self, digest: str) -> tuple[SessionSecrets | None, ConsumedRefresh | None]: ...
    def family(self, family_id: UUID, *, lock: bool = False) -> SessionSecrets | None: ...
    def rotate(self, old: SessionSecrets, new: SessionSecrets, now: datetime) -> None: ...
    def revoke(self, family_id: UUID, now: datetime) -> None: ...
    def revoke_account(self, account_id: UUID, now: datetime) -> None: ...
