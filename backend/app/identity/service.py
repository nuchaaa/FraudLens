"""Human identity workflows; no web framework or SQL dependency."""

import hashlib
import hmac
import json
import re
import secrets
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.app.audit.entities import AuditEvent
from backend.app.identity.policy import (
    HumanAccount,
    IssuedSecrets,
    PasswordVerifier,
    RefreshOutcome,
    SessionFamily,
    validate_password,
)
from backend.app.identity.ports import AccountCredentials, SessionSecrets
from backend.app.shared.ports import UnitOfWork
from backend.app.shared.security import Principal, Role

type UnitOfWorkFactory = Callable[[], AbstractContextManager[UnitOfWork]]

_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_LOGIN = re.compile(r"[a-z][a-z0-9._-]{2,63}\Z")
_DUMMY_PASSWORD = "fixed-invalid-password-for-verification"


class AuthenticationDenied(ValueError):
    """All failed human login/refresh paths map to one public error."""


@dataclass(frozen=True)
class HumanSession:
    account_id: UUID
    principal: Principal
    csrf: str


def token_sha256(value: str) -> str | None:
    if not _TOKEN.fullmatch(value):
        return None
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _new_secrets() -> IssuedSecrets:
    return IssuedSecrets(*(secrets.token_urlsafe(32) for _ in range(3)))


def _state(family: SessionFamily, issued: IssuedSecrets) -> SessionSecrets:
    digests = (token_sha256(item) for item in (issued.access, issued.refresh, issued.csrf))
    access, refresh, csrf = digests
    assert access is not None and refresh is not None and csrf is not None
    return SessionSecrets(family, access, refresh, csrf)


def _audit(
    uow: UnitOfWork,
    actor_id: UUID,
    action: str,
    entity_id: UUID,
    now: datetime,
    detail: str = "human session",
) -> None:
    uow.audit.add(AuditEvent(uuid4(), actor_id, action, entity_id, uuid4(), now, detail))


def _policy_detail(account: HumanAccount, *, password_changed: bool) -> str:
    return json.dumps(
        {
            "role": account.role.value,
            "customer_ids": sorted(str(item) for item in account.customer_ids),
            "active": account.active,
            "authorization_version": account.authorization_version,
            "password_changed": password_changed,
            "expires_at": account.expires_at.isoformat() if account.expires_at else None,
        },
        sort_keys=True,
    )


class IdentityService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        passwords: PasswordVerifier,
        *,
        service_principal_ids: frozenset[UUID] = frozenset(),
    ) -> None:
        self._uow_factory = uow_factory
        self._passwords = passwords
        self._service_ids = service_principal_ids
        self._dummy_hash = passwords.hash(_DUMMY_PASSWORD)

    def ensure_no_collisions(self) -> None:
        with self._uow_factory() as uow:
            for principal_id in self._service_ids:
                if uow.identity.account(principal_id) is not None:
                    raise ValueError("human and service principal IDs overlap")

    def provision(
        self,
        login: str,
        password: str,
        role: Role,
        customer_ids: frozenset[UUID],
        *,
        operator_id: UUID,
        expires_at: datetime | None = None,
    ) -> UUID:
        login = login.lower()
        if not _LOGIN.fullmatch(login):
            raise ValueError("login must be a 3-64 character ASCII identifier")
        validate_password(password)
        account_id = uuid4()
        while account_id in self._service_ids:
            account_id = uuid4()
        account = HumanAccount(account_id, role, customer_ids, expires_at=expires_at)
        encoded = self._passwords.hash(password)
        now = datetime.now(UTC)
        with self._uow_factory() as uow:
            if uow.identity.account_by_login(login) is not None:
                raise ValueError("login already exists")
            uow.identity.add_account(AccountCredentials(account, login, encoded), now)
            _audit(
                uow,
                operator_id,
                "HUMAN_ACCOUNT_PROVISIONED",
                account_id,
                now,
                _policy_detail(account, password_changed=True),
            )
            uow.commit()
        return account_id

    def change(
        self,
        account_id: UUID,
        *,
        operator_id: UUID,
        password: str | None = None,
        role: Role | None = None,
        customer_ids: frozenset[UUID] | None = None,
        active: bool | None = None,
        expires_at: datetime | None = None,
        set_expiry: bool = False,
    ) -> None:
        encoded = self._passwords.hash(password) if password is not None else None
        now = datetime.now(UTC)
        with self._uow_factory() as uow:
            current = uow.identity.account(account_id, lock=True)
            if current is None:
                raise ValueError("account not found")
            next_account = replace(
                current.account,
                role=role if role is not None else current.account.role,
                customer_ids=customer_ids
                if customer_ids is not None
                else current.account.customer_ids,
                active=active if active is not None else current.account.active,
                expires_at=expires_at if set_expiry else current.account.expires_at,
                authorization_version=current.account.authorization_version + 1,
            )
            uow.identity.update_account(
                AccountCredentials(next_account, current.login, encoded or current.password_hash),
                now,
            )
            uow.identity.revoke_account(account_id, now)
            _audit(
                uow,
                operator_id,
                "HUMAN_ACCOUNT_CHANGED",
                account_id,
                now,
                _policy_detail(next_account, password_changed=password is not None),
            )
            uow.commit()

    def login(self, login: str, password: str) -> IssuedSecrets:
        identifier = login.lower() if len(login) <= 64 else "invalid"
        if not _LOGIN.fullmatch(identifier):
            identifier = "invalid"
        now = datetime.now(UTC)
        with self._uow_factory() as uow:
            permitted = uow.identity.reserve_login(identifier, now)
            uow.identity.prune_expired(now)
            uow.commit()
        if not permitted:
            raise AuthenticationDenied("invalid credentials")
        with self._uow_factory() as uow:
            current = uow.identity.account_by_login(identifier)
            encoded = current.password_hash if current else self._dummy_hash
            valid = self._passwords.verify(encoded, password)
            if not valid or current is None or not current.account.enabled_at(now):
                raise AuthenticationDenied("invalid credentials")
            # Account row lock linearizes login with operator revocation.
            locked = uow.identity.account(current.account.account_id, lock=True)
            if (
                locked is None
                or not locked.account.enabled_at(now)
                or locked.account != current.account
            ):
                raise AuthenticationDenied("invalid credentials")
            issued = _new_secrets()
            family = SessionFamily.start(uuid4(), locked.account, now)
            uow.identity.add_session(_state(family, issued))
            _audit(uow, locked.account.account_id, "HUMAN_LOGIN", family.family_id, now)
            uow.commit()
            return issued

    def session(self, access: str, csrf_cookie: str) -> HumanSession | None:
        digest, csrf = token_sha256(access), token_sha256(csrf_cookie)
        if digest is None or csrf is None:
            return None
        now = datetime.now(UTC)
        with self._uow_factory() as uow:
            state = uow.identity.access(digest)
            if state is None or not hmac.compare_digest(csrf, state.csrf_sha256):
                return None
            account = uow.identity.account(state.family.account_id)
            if account is None or not state.family.permits_access(account.account, now):
                return None
            principal = account.account.principal(now)
            return (
                HumanSession(account.account.account_id, principal, csrf_cookie)
                if principal
                else None
            )

    def pending_refresh(self, refresh: str, csrf_cookie: str) -> str | None:
        digest, csrf = token_sha256(refresh), token_sha256(csrf_cookie)
        if digest is None or csrf is None:
            return None
        now = datetime.now(UTC)
        with self._uow_factory() as uow:
            state, _ = uow.identity.refresh(digest)
            if state is None or not hmac.compare_digest(csrf, state.csrf_sha256):
                return None
            account = uow.identity.account(state.family.account_id)
            if account is None or not state.family.current_for(account.account, now):
                return None
            return csrf_cookie

    def refresh(self, refresh: str, csrf_cookie: str, csrf_header: str) -> IssuedSecrets:
        digest, csrf = token_sha256(refresh), token_sha256(csrf_cookie)
        if digest is None or csrf is None or not hmac.compare_digest(csrf_cookie, csrf_header):
            raise AuthenticationDenied("invalid credentials")
        now = datetime.now(UTC)
        with self._uow_factory() as uow:
            current, consumed = uow.identity.refresh(digest)
            family_id = (
                current.family.family_id if current else consumed.family_id if consumed else None
            )
            if family_id is None:
                raise AuthenticationDenied("invalid credentials")
            state = uow.identity.family(family_id, lock=True)
            if state is None:
                raise AuthenticationDenied("invalid credentials")
            account = uow.identity.account(state.family.account_id)
            if account is None:
                raise AuthenticationDenied("invalid credentials")
            # The family lock may have waited for another rotation. Use the clock
            # after the lock, so a replay is evaluated against the committed generation.
            now = datetime.now(UTC)
            if current is not None and not hmac.compare_digest(digest, state.refresh_sha256):
                # Another worker rotated between the first read and this family lock.
                # A fresh statement sees its committed consumed-token record.
                _, consumed = uow.identity.refresh(digest)
            if consumed is not None:
                if (
                    not hmac.compare_digest(csrf, consumed.csrf_sha256)
                    or now >= consumed.expires_at
                ):
                    raise AuthenticationDenied("invalid credentials")
                if (
                    state.family.refresh_outcome(
                        account.account, now, recognized_consumed_token=True
                    )
                    == RefreshOutcome.REVOKE_REUSE
                ):
                    uow.identity.revoke(family_id, now)
                    _audit(uow, account.account.account_id, "HUMAN_REFRESH_REUSE", family_id, now)
                    uow.commit()
                raise AuthenticationDenied("invalid credentials")
            if not hmac.compare_digest(digest, state.refresh_sha256) or not hmac.compare_digest(
                csrf, state.csrf_sha256
            ):
                raise AuthenticationDenied("invalid credentials")
            if (
                state.family.refresh_outcome(account.account, now, recognized_consumed_token=False)
                != RefreshOutcome.ROTATE
            ):
                raise AuthenticationDenied("invalid credentials")
            issued = _new_secrets()
            next_family = state.family.rotate(account.account, now)
            uow.identity.rotate(state, _state(next_family, issued), now)
            _audit(uow, account.account.account_id, "HUMAN_REFRESH", family_id, now)
            uow.commit()
            return issued

    def logout(self, refresh: str, csrf_cookie: str, csrf_header: str) -> None:
        digest, csrf = token_sha256(refresh), token_sha256(csrf_cookie)
        if digest is None or csrf is None or not hmac.compare_digest(csrf_cookie, csrf_header):
            raise AuthenticationDenied("invalid credentials")
        now = datetime.now(UTC)
        with self._uow_factory() as uow:
            current, _ = uow.identity.refresh(digest)
            if current is None:
                raise AuthenticationDenied("invalid credentials")
            state = uow.identity.family(current.family.family_id, lock=True)
            if state is None or not hmac.compare_digest(csrf, state.csrf_sha256):
                raise AuthenticationDenied("invalid credentials")
            account = uow.identity.account(state.family.account_id)
            if account is None or not state.family.current_for(account.account, now):
                raise AuthenticationDenied("invalid credentials")
            uow.identity.revoke(state.family.family_id, now)
            _audit(uow, account.account.account_id, "HUMAN_LOGOUT", state.family.family_id, now)
            uow.commit()
