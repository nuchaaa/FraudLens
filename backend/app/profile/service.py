from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from backend.app.profile.entities import CustomerBehaviorProfile
from backend.app.profile.read_model import (
    BaselineStatus,
    ProfileHistoryUnavailable,
    ProfileQueryError,
    ProfileReadPolicy,
    ProfileView,
    summarize_window,
)
from backend.app.shared.ports import UnitOfWork
from backend.app.shared.security import NotFound, Principal
from backend.app.shared.validation import currency_code, utc


class ProfileService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        policy: ProfileReadPolicy | None = None,
    ) -> None:
        self.uow_factory = uow_factory
        self.clock = clock
        self.policy = policy or ProfileReadPolicy()

    def retrieve(
        self,
        principal: Principal,
        customer_id: UUID,
        currency: str,
        *,
        as_of: datetime | None = None,
        version: int | None = None,
    ) -> ProfileView:
        # Deny before even opening storage, with the same message as a missing customer.
        if not principal.can_read(customer_id):
            raise NotFound("customer not found")
        try:
            currency_code(currency)
            now = utc(self.clock())
            cutoff = utc(as_of) if as_of is not None else now
        except (ValueError, OverflowError) as exc:
            raise ProfileQueryError("invalid currency or timezone-aware cutoff") from exc
        if cutoff > now or (version is not None and version < 1):
            raise ProfileQueryError("future cutoffs and nonpositive versions are not supported")
        if as_of is not None and version is None:
            raise ProfileQueryError("an explicit as_of requires a pinned profile version")
        with self.uow_factory() as uow:
            customer = uow.customers.get(customer_id)
            if customer is None:
                raise NotFound("customer not found")
            profile = uow.profiles.get_revision(customer_id, currency, version=version)
            if profile is None:
                if version is not None:
                    raise NotFound("profile revision not found")
                profile = CustomerBehaviorProfile(
                    customer_id,
                    currency,
                    cutoff,
                    timezone=customer.timezone,
                )
                selected_version, revision_as_of = None, None
            else:
                selected_version, revision_as_of = profile.version, profile.as_of
                if cutoff < profile.as_of:
                    raise ProfileHistoryUnavailable(
                        "cutoff predates this revision; select an earlier captured version"
                    )
                # Strictly before the candidate's instant, including simultaneous transactions.
                profile = replace(
                    profile,
                    as_of=cutoff,
                    observations=tuple(o for o in profile.observations if o.timestamp < cutoff),
                )
            try:
                long_term = summarize_window(profile, profile.long_window_days, self.policy)
                short_term = summarize_window(profile, profile.short_window_days, self.policy)
            except OverflowError as exc:
                raise ProfileQueryError("cutoff cannot represent the profile windows") from exc
            if selected_version is None:
                status = BaselineStatus.UNINITIALIZED
            elif not long_term.count:
                status = BaselineStatus.EMPTY
            elif long_term.count < self.policy.minimum_history:
                status = BaselineStatus.INSUFFICIENT_HISTORY
            else:
                status = BaselineStatus.SUFFICIENT_HISTORY
            return ProfileView(
                customer_id,
                currency,
                cutoff,
                selected_version,
                revision_as_of,
                profile.timezone,
                status,
                self.policy,
                profile.admission_workflow_verified,
                profile.admission_policy_version,
                profile.learning_decision_id,
                long_term,
                short_term,
            )
