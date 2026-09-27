"""Framework-free storage contract for centrally revocable human identities."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
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


class MfaCeremony(StrEnum):
    LOGIN = "LOGIN"
    FIRST_ENROLLMENT = "FIRST_ENROLLMENT"
    ADD_FACTOR_PROOF = "ADD_FACTOR_PROOF"
    ADD_FACTOR_REGISTER = "ADD_FACTOR_REGISTER"
    REMOVE_FACTOR_PROOF = "REMOVE_FACTOR_PROOF"


@dataclass(frozen=True)
class MfaCredential:
    credential_id: bytes
    account_id: UUID
    public_key: bytes
    sign_count: int
    device_type: str
    backed_up: bool
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class MfaChallenge:
    challenge_id: UUID
    account_id: UUID
    ceremony: MfaCeremony
    challenge: bytes
    rp_id: str
    origin: str
    authorization_version: int
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None
    session_family_id: UUID | None = None
    target_credential_id: bytes | None = None


@dataclass(frozen=True)
class VerifiedMfaCredential:
    credential_id: bytes
    public_key: bytes
    sign_count: int
    device_type: str
    backed_up: bool


class InvalidMfaResponse(ValueError):
    """A credential response failed parsing or cryptographic verification."""


class WebAuthnVerifier(Protocol):
    def credential_id(self, response: dict[str, object]) -> bytes: ...
    def registration_options(
        self, *, rp_id: str, account_id: UUID, login: str, challenge: bytes
    ) -> dict[str, object]: ...
    def verify_registration(
        self, *, response: dict[str, object], challenge: bytes, rp_id: str, origin: str
    ) -> VerifiedMfaCredential: ...
    def authentication_options(
        self, *, rp_id: str, challenge: bytes, credential_ids: tuple[bytes, ...]
    ) -> dict[str, object]: ...
    def verify_authentication(
        self,
        *,
        response: dict[str, object],
        challenge: bytes,
        rp_id: str,
        origin: str,
        credential: MfaCredential,
    ) -> int: ...


class IdentityRepository(Protocol):
    def lock_account(self, account_id: UUID) -> None: ...
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
    def active_credentials(self, account_id: UUID) -> tuple[MfaCredential, ...]: ...
    def credential(self, credential_id: bytes, *, lock: bool = False) -> MfaCredential | None: ...
    def add_credential(self, credential: MfaCredential) -> None: ...
    def use_credential(self, credential_id: bytes, sign_count: int, now: datetime) -> None: ...
    def revoke_credential(self, credential_id: bytes, now: datetime) -> None: ...
    def add_challenge(self, challenge: MfaChallenge) -> None: ...
    def challenge(self, challenge_id: UUID, *, lock: bool = False) -> MfaChallenge | None: ...
    def consume_challenge(self, challenge_id: UUID, now: datetime) -> None: ...
    def prune_mfa_challenges(self) -> None: ...
