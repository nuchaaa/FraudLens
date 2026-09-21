from datetime import timedelta
from uuid import UUID

from sqlalchemy import select

from backend.adapters.database.codec import decode_profile, encode_profile
from backend.adapters.database.models import (
    ObservationRow,
    ProfileRevisionRow,
    ProfileRow,
    SnapshotRow,
    TransactionRow,
)
from backend.adapters.database.repository_base import Repository
from backend.app.profile.entities import (
    CustomerBehaviorProfile,
    ProfileObservation,
    ProfileSnapshot,
)
from backend.app.shared.errors import ConcurrentUpdate, HistoryConflict


class PostgresCustomerProfileRepository(Repository):
    def get_revision(
        self,
        customer_id: UUID,
        currency: str,
        *,
        version: int | None = None,
    ) -> CustomerBehaviorProfile | None:
        query = select(ProfileRevisionRow).where(
            ProfileRevisionRow.customer_id == customer_id,
            ProfileRevisionRow.currency == currency,
        )
        if version is not None:
            query = query.where(ProfileRevisionRow.version == version)
        row = self.session.scalar(query.order_by(ProfileRevisionRow.version.desc()).limit(1))
        return self._hydrate(row) if row is not None else None

    def get(self, customer_id: UUID, currency: str) -> CustomerBehaviorProfile | None:
        row = self.session.get(ProfileRow, (customer_id, currency), populate_existing=True)
        if row is None:
            return None
        return self._hydrate(row)

    def get_for_update(self, customer_id: UUID, currency: str) -> CustomerBehaviorProfile | None:
        row = self.session.scalar(
            select(ProfileRow)
            .where(ProfileRow.customer_id == customer_id, ProfileRow.currency == currency)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self._hydrate(row) if row is not None else None

    def _hydrate(self, row: ProfileRow | ProfileRevisionRow) -> CustomerBehaviorProfile:
        # One statement for the immutable observations; reads use the captured head's time.
        transactions = self.session.scalars(
            select(TransactionRow)
            .join(ObservationRow, TransactionRow.transaction_id == ObservationRow.transaction_id)
            .where(
                ObservationRow.customer_id == row.customer_id,
                ObservationRow.currency == row.currency,
                ObservationRow.admitted_version <= row.version,
                TransactionRow.timestamp > row.as_of - timedelta(days=row.long_window_days),
                TransactionRow.timestamp <= row.as_of,
            )
            .order_by(ObservationRow.ordinal)
        ).all()
        return CustomerBehaviorProfile(
            row.customer_id,
            row.currency,
            row.as_of,
            tuple(
                ProfileObservation(t.transaction_id, t.amount, t.timestamp, t.recipient_id)
                for t in transactions
            ),
            row.version,
            row.timezone,
            row.long_window_days,
            row.short_window_days,
            row.admission_workflow_verified,
            row.admission_policy_version,
            row.learning_decision_id,
        )

    def save(self, profile: CustomerBehaviorProfile, *, expected_version: int) -> None:
        if expected_version < 0 or profile.version != expected_version + 1:
            raise ConcurrentUpdate(
                "profile version must advance exactly once; creation expects zero"
            )
        row = self.session.scalar(
            select(ProfileRow)
            .where(
                ProfileRow.customer_id == profile.customer_id,
                ProfileRow.currency == profile.currency,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            if expected_version != 0:
                raise ConcurrentUpdate("profile no longer exists")
            row = ProfileRow(
                customer_id=profile.customer_id,
                currency=profile.currency,
                version=profile.version,
                as_of=profile.as_of,
                timezone=profile.timezone,
                long_window_days=profile.long_window_days,
                short_window_days=profile.short_window_days,
                admission_workflow_verified=profile.admission_workflow_verified,
                admission_policy_version=profile.admission_policy_version,
                learning_decision_id=profile.learning_decision_id,
            )
            self.session.add(row)
            self.session.flush()
        elif row.version != expected_version:
            raise ConcurrentUpdate("profile changed since it was read")
        elif profile.as_of < row.as_of:
            raise HistoryConflict("profile time cannot move backwards")
        admitted = self.session.scalars(
            select(ObservationRow)
            .where(
                ObservationRow.customer_id == profile.customer_id,
                ObservationRow.currency == profile.currency,
            )
            .order_by(ObservationRow.ordinal)
        ).all()
        original_ids = {o.transaction_id for o in admitted}
        cutoff = profile.as_of - timedelta(days=profile.long_window_days)
        original_transactions = {
            t.transaction_id: t
            for t in self.session.scalars(
                select(TransactionRow).where(TransactionRow.transaction_id.in_(original_ids))
            )
        }
        active_ids = {
            t.transaction_id for t in original_transactions.values() if cutoff < t.timestamp
        }
        proposed_ids = {o.transaction_id for o in profile.observations}
        if not active_ids <= proposed_ids:
            raise HistoryConflict("cannot remove observations still inside the profile window")
        ordinal = len(admitted)
        for observation in profile.observations:
            tx = self.session.get(TransactionRow, observation.transaction_id)
            if tx is None or (
                tx.customer_id,
                tx.currency,
                tx.amount,
                tx.timestamp,
                tx.recipient_id,
            ) != (
                profile.customer_id,
                profile.currency,
                observation.amount,
                observation.timestamp,
                observation.recipient_id,
            ):
                raise HistoryConflict("observation must match its persisted transaction")
            if observation.transaction_id not in original_ids:
                self.session.add(
                    ObservationRow(
                        transaction_id=observation.transaction_id,
                        customer_id=profile.customer_id,
                        currency=profile.currency,
                        admitted_version=profile.version,
                        ordinal=ordinal,
                    )
                )
                ordinal += 1
        row.version, row.as_of, row.timezone = profile.version, profile.as_of, profile.timezone
        row.long_window_days, row.short_window_days = (
            profile.long_window_days,
            profile.short_window_days,
        )
        row.admission_workflow_verified = profile.admission_workflow_verified
        row.admission_policy_version = profile.admission_policy_version
        row.learning_decision_id = profile.learning_decision_id
        self.session.flush()


class PostgresSnapshotRepository(Repository):
    def add(self, snapshot: ProfileSnapshot) -> None:
        self.session.add(
            SnapshotRow(
                snapshot_id=snapshot.snapshot_id,
                assessment_id=snapshot.assessment_id,
                customer_id=snapshot.profile.customer_id,
                currency=snapshot.profile.currency,
                profile=encode_profile(snapshot.profile),
            )
        )
        self.session.flush()

    def get(self, snapshot_id: UUID) -> ProfileSnapshot | None:
        row = self.session.get(SnapshotRow, snapshot_id)
        return (
            ProfileSnapshot(row.snapshot_id, row.assessment_id, decode_profile(row.profile))
            if row
            else None
        )
