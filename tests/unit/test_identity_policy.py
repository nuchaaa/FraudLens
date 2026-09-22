from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from backend.adapters.passwords import Argon2Passwords
from backend.app.identity.policy import (
    HumanAccount,
    IssuedSecrets,
    RefreshOutcome,
    SessionFamily,
    validate_password,
)
from backend.app.shared.security import Role

NOW = datetime(2026, 9, 22, tzinfo=UTC)


@pytest.fixture
def account():
    return HumanAccount(uuid4(), Role.ANALYST, frozenset({uuid4()}))


@pytest.fixture
def family(account):
    return SessionFamily.start(uuid4(), account, NOW)


def test_human_identity_preserves_scope_and_cannot_be_machine(account):
    principal = account.principal(NOW)
    assert principal.principal_id == account.account_id
    assert principal.can_read(next(iter(account.customer_ids)))
    assert not principal.can_read(uuid4())
    assert not principal.can_submit(next(iter(account.customer_ids)))
    with pytest.raises(ValueError):
        replace(account, role=Role.SERVICE)
    with pytest.raises(ValueError):
        replace(account, role=Role.ADMIN)


@pytest.mark.parametrize("version", [0, -1, True, 1.5])
def test_authorization_version_is_positive_integer(account, version):
    with pytest.raises(ValueError):
        replace(account, authorization_version=version)


@pytest.mark.parametrize("seconds,allowed", [(-1, False), (0, True), (299, True), (300, False)])
def test_access_expiry_is_exclusive(account, family, seconds, allowed):
    assert family.permits_access(account, NOW + timedelta(seconds=seconds)) is allowed


@pytest.mark.parametrize("seconds,allowed", [(1799, True), (1800, False), (1801, False)])
def test_refresh_idle_boundary(account, family, seconds, allowed):
    assert family.current_for(account, NOW + timedelta(seconds=seconds)) is allowed


def test_refresh_survives_access_expiry_but_not_account_changes(account, family):
    now = NOW + timedelta(minutes=6)
    assert not family.permits_access(account, now)
    rotated = family.rotate(account, now)
    assert rotated.permits_access(account, now)
    assert rotated.generation == 2
    assert rotated.absolute_expires_at == family.absolute_expires_at
    for changed in (
        replace(account, active=False),
        replace(account, authorization_version=2),
        replace(account, account_id=uuid4()),
        replace(account, expires_at=now),
    ):
        assert not rotated.permits_access(changed, now)
        assert (
            rotated.refresh_outcome(changed, now, recognized_consumed_token=False)
            == RefreshOutcome.DENY
        )
        with pytest.raises(ValueError):
            rotated.rotate(changed, now)


def test_rotation_never_extends_absolute_lifetime(account, family):
    current = family
    for minute in range(20, 480, 20):
        current = current.rotate(account, NOW + timedelta(minutes=minute))
    near_end = NOW + timedelta(hours=8, seconds=-1)
    current = current.rotate(account, near_end)
    assert current.access_expires_at == family.absolute_expires_at
    assert current.idle_expires_at == family.absolute_expires_at
    assert current.permits_access(account, near_end)
    assert not current.permits_access(account, family.absolute_expires_at)
    with pytest.raises(ValueError):
        current.rotate(account, family.absolute_expires_at)


def test_recognized_refresh_reuse_requires_family_revocation(account, family):
    now = NOW + timedelta(minutes=1)
    rotated = family.rotate(account, now)
    assert (
        rotated.refresh_outcome(account, now, recognized_consumed_token=True)
        == RefreshOutcome.REVOKE_REUSE
    )
    revoked = rotated.revoke(now)
    assert not revoked.permits_access(account, now)
    assert (
        revoked.refresh_outcome(account, now, recognized_consumed_token=False)
        == RefreshOutcome.DENY
    )
    assert revoked.revoke(now + timedelta(seconds=1)) == revoked


def test_inactive_or_expired_accounts_cannot_start_sessions(account):
    for changed in (replace(account, active=False), replace(account, expires_at=NOW)):
        assert changed.principal(NOW) is None
        with pytest.raises(ValueError):
            SessionFamily.start(uuid4(), changed, NOW)


@pytest.mark.parametrize(
    "field,value",
    [
        ("generation", 0),
        ("generation", True),
        ("rotated_at", NOW - timedelta(seconds=1)),
        ("access_expires_at", NOW),
        ("access_expires_at", NOW + timedelta(minutes=6)),
        ("idle_expires_at", NOW + timedelta(minutes=31)),
        ("absolute_expires_at", NOW + timedelta(hours=9)),
        ("revoked_at", NOW - timedelta(seconds=1)),
        ("created_at", NOW.replace(tzinfo=None)),
    ],
)
def test_invalid_session_state_rejected(family, field, value):
    with pytest.raises(ValueError):
        replace(family, **{field: value})


@pytest.mark.parametrize("password", ["", "a" * 14, "a" * 129, "\ud800" * 15])
def test_password_input_bounded_without_echoing_secret(password):
    with pytest.raises(ValueError, match="password must contain"):
        validate_password(password)
    assert not Argon2Passwords().verify("invalid", password)


def test_argon2_real_hash_salt_policy_and_exact_password():
    passwords = Argon2Passwords()
    password = "  synthetic password phrase  "
    first = passwords.hash(password)
    second = passwords.hash(password)
    assert first != second
    assert first.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert passwords.verify(first, password)
    assert not passwords.verify(first, password.strip())
    assert not passwords.verify(first, "another synthetic password")
    assert not passwords.needs_rehash(first)
    assert passwords.needs_rehash("not-an-encoded-hash")
    assert not passwords.verify("not-an-encoded-hash", password)


def test_unicode_password_is_not_normalized():
    passwords = Argon2Passwords()
    password = "synthetic caf\u00e9 password"
    encoded = passwords.hash(password)
    assert passwords.verify(encoded, password)
    assert not passwords.verify(encoded, "synthetic cafe\u0301 password")


def test_issued_secrets_not_in_repr():
    assert (
        repr(IssuedSecrets("access-secret", "refresh-secret", "csrf-secret")) == "IssuedSecrets()"
    )
