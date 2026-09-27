"""PostgreSQL identity persistence; family/account locks serialize revocation."""

import hashlib
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert

from backend.adapters.database.models import (
    ConsumedRefreshRow,
    HumanAccountRow,
    HumanAuthenticatorRow,
    HumanMfaChallengeRow,
    HumanSessionRow,
    LoginThrottleRow,
)
from backend.adapters.database.repository_base import Repository
from backend.app.identity.policy import HumanAccount, SessionFamily
from backend.app.identity.ports import (
    AccountCredentials,
    ConsumedRefresh,
    MfaCeremony,
    MfaChallenge,
    MfaCredential,
    SessionSecrets,
)
from backend.app.shared.security import Role


def _account(row: HumanAccountRow) -> AccountCredentials:
    return AccountCredentials(
        HumanAccount(
            row.account_id,
            Role(row.role),
            frozenset(row.customer_ids),
            row.active,
            row.authorization_version,
            row.expires_at,
        ),
        row.login,
        row.password_hash,
    )


def _session(row: HumanSessionRow) -> SessionSecrets:
    return SessionSecrets(
        SessionFamily(
            row.family_id,
            row.account_id,
            row.authorization_version,
            row.created_at,
            row.rotated_at,
            row.access_expires_at,
            row.idle_expires_at,
            row.absolute_expires_at,
            row.generation,
            row.revoked_at,
        ),
        row.access_sha256,
        row.refresh_sha256,
        row.csrf_sha256,
    )


def _credential(row: HumanAuthenticatorRow) -> MfaCredential:
    return MfaCredential(
        bytes(row.credential_id),
        row.account_id,
        bytes(row.public_key),
        row.sign_count,
        row.device_type,
        row.backed_up,
        row.created_at,
        row.last_used_at,
        row.revoked_at,
    )


def _challenge(row: HumanMfaChallengeRow) -> MfaChallenge:
    return MfaChallenge(
        row.challenge_id,
        row.account_id,
        MfaCeremony(row.ceremony),
        bytes(row.challenge),
        row.rp_id,
        row.origin,
        row.authorization_version,
        row.created_at,
        row.expires_at,
        row.consumed_at,
        row.session_family_id,
        bytes(row.target_credential_id) if row.target_credential_id is not None else None,
    )


class PostgresIdentityRepository(Repository):
    def lock_account(self, account_id: UUID) -> None:
        digest = hashlib.sha256(b"fraudlens-human-account-v1:" + account_id.bytes).digest()
        lock_id = int.from_bytes(digest[:8], "big", signed=True)
        self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})

    def account_by_login(self, login: str) -> AccountCredentials | None:
        row = self.session.scalar(select(HumanAccountRow).where(HumanAccountRow.login == login))
        return _account(row) if row else None

    def account(self, account_id: UUID, *, lock: bool = False) -> AccountCredentials | None:
        query = select(HumanAccountRow).where(HumanAccountRow.account_id == account_id)
        row = self.session.scalar(
            (query.with_for_update() if lock else query).execution_options(populate_existing=True)
        )
        return _account(row) if row else None

    def add_account(self, account: AccountCredentials, now: datetime) -> None:
        self.session.add(
            HumanAccountRow(
                account_id=account.account.account_id,
                login=account.login,
                password_hash=account.password_hash,
                role=account.account.role.value,
                customer_ids=sorted(account.account.customer_ids),
                active=account.account.active,
                authorization_version=account.account.authorization_version,
                expires_at=account.account.expires_at,
                created_at=now,
                updated_at=now,
            )
        )
        self.session.flush()

    def update_account(self, account: AccountCredentials, now: datetime) -> None:
        self.session.execute(
            update(HumanAccountRow)
            .where(HumanAccountRow.account_id == account.account.account_id)
            .values(
                password_hash=account.password_hash,
                role=account.account.role.value,
                customer_ids=sorted(account.account.customer_ids),
                active=account.account.active,
                authorization_version=account.account.authorization_version,
                expires_at=account.account.expires_at,
                updated_at=now,
            )
        )

    def reserve_login(self, login: str, now: datetime) -> bool:
        # Fixed 256 identifier buckets keep state bounded even for random usernames.
        bucket = hashlib.sha256(login.encode()).hexdigest()[:2]
        for key, limit in (("global", 100), (f"u-{bucket}", 10)):
            statement = (
                insert(LoginThrottleRow)
                .values(bucket=key, window_started_at=now, attempts=1)
                .on_conflict_do_nothing(index_elements=[LoginThrottleRow.bucket])
                .returning(LoginThrottleRow.bucket)
            )
            # One row lock per fixed bucket. Reset windows with a locked read.
            inserted = self.session.execute(statement).scalar_one_or_none() is not None
            row = self.session.scalar(
                select(LoginThrottleRow)
                .where(LoginThrottleRow.bucket == key)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            assert row is not None
            if row.window_started_at <= now - timedelta(minutes=1):
                row.window_started_at, row.attempts = now, 1
            elif not inserted:
                row.attempts += 1
            if row.attempts > limit:
                self.session.flush()
                return False
        self.session.flush()
        return True

    def prune_expired(self, now: datetime) -> None:
        expired = (
            select(ConsumedRefreshRow.refresh_sha256)
            .where(ConsumedRefreshRow.expires_at <= now)
            .order_by(ConsumedRefreshRow.expires_at)
            .limit(100)
        )
        self.session.execute(
            delete(ConsumedRefreshRow).where(ConsumedRefreshRow.refresh_sha256.in_(expired))
        )

    def add_session(self, state: SessionSecrets) -> None:
        family = state.family
        self.session.add(
            HumanSessionRow(
                family_id=family.family_id,
                account_id=family.account_id,
                authorization_version=family.authorization_version,
                created_at=family.created_at,
                rotated_at=family.rotated_at,
                access_expires_at=family.access_expires_at,
                idle_expires_at=family.idle_expires_at,
                absolute_expires_at=family.absolute_expires_at,
                generation=family.generation,
                revoked_at=family.revoked_at,
                access_sha256=state.access_sha256,
                refresh_sha256=state.refresh_sha256,
                csrf_sha256=state.csrf_sha256,
            )
        )
        self.session.flush()

    def access(self, digest: str) -> SessionSecrets | None:
        row = self.session.scalar(
            select(HumanSessionRow).where(HumanSessionRow.access_sha256 == digest)
        )
        return _session(row) if row else None

    def refresh(self, digest: str) -> tuple[SessionSecrets | None, ConsumedRefresh | None]:
        row = self.session.scalar(
            select(HumanSessionRow).where(HumanSessionRow.refresh_sha256 == digest)
        )
        if row:
            return _session(row), None
        consumed = self.session.get(ConsumedRefreshRow, digest)
        if consumed:
            return None, ConsumedRefresh(
                consumed.family_id, consumed.csrf_sha256, consumed.expires_at
            )
        return None, None

    def family(self, family_id: UUID, *, lock: bool = False) -> SessionSecrets | None:
        query = select(HumanSessionRow).where(HumanSessionRow.family_id == family_id)
        row = self.session.scalar(
            (query.with_for_update() if lock else query).execution_options(populate_existing=True)
        )
        return _session(row) if row else None

    def rotate(self, old: SessionSecrets, new: SessionSecrets, now: datetime) -> None:
        self.session.add(
            ConsumedRefreshRow(
                refresh_sha256=old.refresh_sha256,
                family_id=old.family.family_id,
                csrf_sha256=old.csrf_sha256,
                consumed_at=now,
                expires_at=old.family.absolute_expires_at,
            )
        )
        self.session.execute(
            update(HumanSessionRow)
            .where(HumanSessionRow.family_id == old.family.family_id)
            .values(
                generation=new.family.generation,
                rotated_at=new.family.rotated_at,
                access_expires_at=new.family.access_expires_at,
                idle_expires_at=new.family.idle_expires_at,
                access_sha256=new.access_sha256,
                refresh_sha256=new.refresh_sha256,
                csrf_sha256=new.csrf_sha256,
            )
        )
        self.session.flush()

    def revoke(self, family_id: UUID, now: datetime) -> None:
        self.session.execute(
            update(HumanSessionRow)
            .where(HumanSessionRow.family_id == family_id, HumanSessionRow.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def revoke_account(self, account_id: UUID, now: datetime) -> None:
        self.session.execute(
            update(HumanSessionRow)
            .where(HumanSessionRow.account_id == account_id, HumanSessionRow.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def active_credentials(self, account_id: UUID) -> tuple[MfaCredential, ...]:
        rows = self.session.scalars(
            select(HumanAuthenticatorRow)
            .where(
                HumanAuthenticatorRow.account_id == account_id,
                HumanAuthenticatorRow.revoked_at.is_(None),
            )
            .order_by(HumanAuthenticatorRow.created_at, HumanAuthenticatorRow.credential_id)
        )
        return tuple(_credential(row) for row in rows)

    def credential(self, credential_id: bytes, *, lock: bool = False) -> MfaCredential | None:
        query = select(HumanAuthenticatorRow).where(
            HumanAuthenticatorRow.credential_id == credential_id
        )
        row = self.session.scalar(
            (query.with_for_update() if lock else query).execution_options(populate_existing=True)
        )
        return _credential(row) if row else None

    def add_credential(self, credential: MfaCredential) -> None:
        self.session.add(
            HumanAuthenticatorRow(
                credential_id=credential.credential_id,
                account_id=credential.account_id,
                public_key=credential.public_key,
                sign_count=credential.sign_count,
                device_type=credential.device_type,
                backed_up=credential.backed_up,
                created_at=credential.created_at,
                last_used_at=credential.last_used_at,
                revoked_at=credential.revoked_at,
            )
        )
        self.session.flush()

    def use_credential(self, credential_id: bytes, sign_count: int, now: datetime) -> None:
        self.session.execute(
            update(HumanAuthenticatorRow)
            .where(
                HumanAuthenticatorRow.credential_id == credential_id,
                HumanAuthenticatorRow.revoked_at.is_(None),
            )
            .values(sign_count=sign_count, last_used_at=now)
        )

    def revoke_credential(self, credential_id: bytes, now: datetime) -> None:
        self.session.execute(
            update(HumanAuthenticatorRow)
            .where(
                HumanAuthenticatorRow.credential_id == credential_id,
                HumanAuthenticatorRow.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    def add_challenge(self, challenge: MfaChallenge) -> None:
        self.prune_mfa_challenges()
        self.session.add(
            HumanMfaChallengeRow(
                challenge_id=challenge.challenge_id,
                account_id=challenge.account_id,
                ceremony=challenge.ceremony.value,
                challenge=challenge.challenge,
                rp_id=challenge.rp_id,
                origin=challenge.origin,
                authorization_version=challenge.authorization_version,
                created_at=challenge.created_at,
                expires_at=challenge.expires_at,
                consumed_at=challenge.consumed_at,
                session_family_id=challenge.session_family_id,
                target_credential_id=challenge.target_credential_id,
            )
        )
        self.session.flush()

    def challenge(self, challenge_id: UUID, *, lock: bool = False) -> MfaChallenge | None:
        query = select(HumanMfaChallengeRow).where(
            HumanMfaChallengeRow.challenge_id == challenge_id
        )
        row = self.session.scalar(
            (query.with_for_update() if lock else query).execution_options(populate_existing=True)
        )
        return _challenge(row) if row else None

    def consume_challenge(self, challenge_id: UUID, now: datetime) -> None:
        self.session.execute(
            update(HumanMfaChallengeRow)
            .where(
                HumanMfaChallengeRow.challenge_id == challenge_id,
                HumanMfaChallengeRow.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )

    def prune_mfa_challenges(self) -> None:
        self.session.execute(
            text("""
            DELETE FROM human_mfa_challenges WHERE challenge_id IN (
                SELECT challenge_id FROM human_mfa_challenges
                WHERE expires_at < statement_timestamp() - INTERVAL '1 day'
                ORDER BY expires_at, challenge_id
                LIMIT 100 FOR UPDATE SKIP LOCKED
            )
        """)
        )
