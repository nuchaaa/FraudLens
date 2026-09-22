"""Pure policy used by future atomic human-session workflows.

This module does not authenticate HTTP requests or persist token state. Callers must
serialize refresh/revocation and retain consumed digests, as specified in ADR-021.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from backend.app.shared.security import Principal, Role
from backend.app.shared.validation import utc

ACCESS_LIFETIME = timedelta(minutes=5)
REFRESH_IDLE_LIFETIME = timedelta(minutes=30)
SESSION_LIFETIME = timedelta(hours=8)


def validate_password(password: str) -> None:
    """Bound work without modifying the user's exact secret."""
    try:
        valid = 15 <= len(password) <= 128 and len(password.encode("utf-8")) <= 512
    except UnicodeEncodeError:
        valid = False
    if not valid:
        raise ValueError("password must contain 15 to 128 valid Unicode characters")


class PasswordVerifier(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, encoded: str, password: str) -> bool: ...
    def needs_rehash(self, encoded: str) -> bool: ...


@dataclass(frozen=True)
class HumanAccount:
    account_id: UUID
    role: Role
    customer_ids: frozenset[UUID] = frozenset()
    active: bool = True
    authorization_version: int = 1
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.role not in (Role.ADMIN, Role.ANALYST):
            raise ValueError("human accounts require an analyst or admin role")
        if type(self.authorization_version) is not int or self.authorization_version < 1:
            raise ValueError("authorization version must be a positive integer")
        if self.role == Role.ADMIN and self.customer_ids:
            raise ValueError("admin scope is unrestricted; do not attach customer scope")
        if self.expires_at is not None:
            object.__setattr__(self, "expires_at", utc(self.expires_at))

    def enabled_at(self, now: datetime) -> bool:
        now = utc(now)
        return self.active and (self.expires_at is None or now < self.expires_at)

    def principal(self, now: datetime) -> Principal | None:
        if not self.enabled_at(now):
            return None
        return Principal(self.account_id, frozenset({self.role}), self.customer_ids)


class RefreshOutcome(StrEnum):
    ROTATE = "ROTATE"
    DENY = "DENY"
    REVOKE_REUSE = "REVOKE_REUSE"


@dataclass(frozen=True)
class SessionFamily:
    family_id: UUID
    account_id: UUID
    authorization_version: int
    created_at: datetime
    rotated_at: datetime
    access_expires_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    generation: int = 1
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        for name in (
            "created_at",
            "rotated_at",
            "access_expires_at",
            "idle_expires_at",
            "absolute_expires_at",
        ):
            object.__setattr__(self, name, utc(getattr(self, name)))
        if self.revoked_at is not None:
            object.__setattr__(self, "revoked_at", utc(self.revoked_at))
        if any(type(v) is not int or v < 1 for v in (self.generation, self.authorization_version)):
            raise ValueError("session versions must be positive integers")
        if not (
            self.created_at
            <= self.rotated_at
            < self.access_expires_at
            <= self.idle_expires_at
            <= self.absolute_expires_at
            <= self.created_at + SESSION_LIFETIME
        ):
            raise ValueError("invalid session chronology")
        if (
            self.access_expires_at > self.rotated_at + ACCESS_LIFETIME
            or self.idle_expires_at > self.rotated_at + REFRESH_IDLE_LIFETIME
            or (self.revoked_at is not None and self.revoked_at < self.rotated_at)
        ):
            raise ValueError("invalid session deadline")

    @classmethod
    def start(cls, family_id: UUID, account: HumanAccount, now: datetime) -> "SessionFamily":
        now = utc(now)
        if not account.enabled_at(now):
            raise ValueError("account unavailable")
        return cls(
            family_id,
            account.account_id,
            account.authorization_version,
            now,
            now,
            now + ACCESS_LIFETIME,
            now + REFRESH_IDLE_LIFETIME,
            now + SESSION_LIFETIME,
        )

    def current_for(self, account: HumanAccount, now: datetime) -> bool:
        now = utc(now)
        return (
            self.revoked_at is None
            and self.account_id == account.account_id
            and self.authorization_version == account.authorization_version
            and account.enabled_at(now)
            and self.rotated_at <= now < min(self.idle_expires_at, self.absolute_expires_at)
        )

    def permits_access(self, account: HumanAccount, now: datetime) -> bool:
        return self.current_for(account, now) and utc(now) < self.access_expires_at

    def refresh_outcome(
        self,
        account: HumanAccount,
        now: datetime,
        *,
        recognized_consumed_token: bool,
    ) -> RefreshOutcome:
        # Caller has already verified token ownership AND origin/CSRF. An unknown
        # digest must never be passed here as a recognized current/consumed token.
        if not self.current_for(account, now):
            return RefreshOutcome.DENY
        if recognized_consumed_token:
            return RefreshOutcome.REVOKE_REUSE
        return RefreshOutcome.ROTATE

    def rotate(self, account: HumanAccount, now: datetime) -> "SessionFamily":
        now = utc(now)
        if not self.current_for(account, now):
            raise ValueError("session unavailable")
        return replace(
            self,
            generation=self.generation + 1,
            rotated_at=now,
            access_expires_at=min(now + ACCESS_LIFETIME, self.absolute_expires_at),
            idle_expires_at=min(now + REFRESH_IDLE_LIFETIME, self.absolute_expires_at),
        )

    def revoke(self, now: datetime) -> "SessionFamily":
        if self.revoked_at is not None:
            return self
        return replace(self, revoked_at=utc(now))


@dataclass(frozen=True)
class IssuedSecrets:
    """Never put bearer secrets in repr, audit details or durable response storage."""

    access: str = field(repr=False)
    refresh: str = field(repr=False)
    csrf: str = field(repr=False)
