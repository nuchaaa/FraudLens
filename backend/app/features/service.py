from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.app.features.context import (
    ACTIVITY_WINDOW_DAYS,
    MAX_ACTIVITY_ROWS,
    ContextSource,
    FeatureContext,
    FeatureInputError,
)
from backend.app.shared.ports import UnitOfWork
from backend.app.shared.security import NotFound, Principal


class FeatureService:
    """Read-only capture. Retain the returned context before any future prediction."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.uow_factory = uow_factory
        self.clock = clock

    def capture(
        self,
        principal: Principal,
        transaction_id: UUID,
        *,
        profile_version: int | None,
    ) -> FeatureContext:
        with self.uow_factory() as uow:
            return self.capture_in(uow, principal, transaction_id, profile_version=profile_version)

    def capture_in(
        self,
        uow: UnitOfWork,
        principal: Principal,
        transaction_id: UUID,
        *,
        profile_version: int | None,
    ) -> FeatureContext:
        if profile_version is not None and profile_version < 1:
            raise FeatureInputError("profile version must be positive or explicitly absent")
        tx = uow.transactions.get(transaction_id)
        if tx is None or not principal.can_read(tx.customer_id):
            raise NotFound("transaction not found")
        customer = uow.customers.get(tx.customer_id)
        if customer is None:
            raise NotFound("customer not found")
        profile = uow.profiles.get_revision(tx.customer_id, tx.currency, version=profile_version)
        if profile_version is None and profile is not None:
            raise FeatureInputError("existing profile requires an explicit captured revision")
        if profile_version is not None and profile is None:
            raise NotFound("profile revision not found")
        try:
            since = tx.timestamp - timedelta(days=ACTIVITY_WINDOW_DAYS)
        except OverflowError as exc:
            raise FeatureInputError("candidate time cannot represent activity window") from exc
        activity = uow.transactions.history_before(
            tx.customer_id,
            tx.currency,
            since=since,
            before=tx.timestamp,
            exclude_transaction_id=tx.transaction_id,
            limit=MAX_ACTIVITY_ROWS,
        )
        return FeatureContext(
            uuid4(),
            tx,
            profile,
            customer.timezone,
            activity,
            self.clock(),
            ContextSource.DATABASE_CAPTURE,
        )
