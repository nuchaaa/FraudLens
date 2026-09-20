from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from backend.app.profile.entities import Customer
from backend.app.profile.read_model import (
    BaselineStatus,
    ProfileHistoryUnavailable,
    ProfileQueryError,
    ProfileReadPolicy,
    summarize_window,
)
from backend.app.profile.service import ProfileService
from backend.app.shared.security import NotFound, Principal, Role


def service_for(profile):
    uow = MagicMock()
    uow.__enter__.return_value = uow
    uow.customers.get.return_value = Customer(profile.customer_id, profile.as_of)
    uow.profiles.get_revision.return_value = profile
    service = ProfileService(lambda: uow, clock=lambda: profile.as_of + timedelta(days=1))
    principal = Principal(uuid4(), frozenset({Role.ANALYST}), frozenset({profile.customer_id}))
    return service, principal, uow


def test_descriptive_frequency_and_frequency_qualified_hours(profile):
    rare = replace(
        profile.observations[0],
        transaction_id=uuid4(),
        timestamp=profile.as_of - timedelta(hours=1),
    )
    profile = replace(profile, observations=(*profile.observations, rare))
    window = summarize_window(profile, 30, ProfileReadPolicy())
    assert window.count == 21 and window.observations_per_day == Decimal("0.7")
    assert window.local_hour_counts[11] == 1 and window.local_hour_counts[12] == 20
    assert window.typical_local_hours == (12,)
    assert len(window.known_recipients) == 1


def test_local_hour_counts_handle_repeated_dst_hour(profile):
    instants = (datetime(2025, 11, 2, 5, 30, tzinfo=UTC), datetime(2025, 11, 2, 6, 30, tzinfo=UTC))
    observations = tuple(
        replace(profile.observations[i], timestamp=instant) for i, instant in enumerate(instants)
    )
    profile = replace(
        profile,
        timezone="America/New_York",
        observations=observations,
        as_of=datetime(2025, 11, 3, tzinfo=UTC),
    )
    window = summarize_window(profile, 30, ProfileReadPolicy())
    assert window.local_hour_counts[1] == 2 and sum(window.local_hour_counts) == 2
    assert window.typical_local_hours == (1,)


@pytest.mark.parametrize(
    "count,status",
    [
        (0, BaselineStatus.EMPTY),
        (1, BaselineStatus.INSUFFICIENT_HISTORY),
        (4, BaselineStatus.INSUFFICIENT_HISTORY),
        (5, BaselineStatus.SUFFICIENT_HISTORY),
    ],
)
def test_explicit_baseline_states(profile, count, status):
    profile = replace(profile, observations=profile.observations[:count])
    service, principal, uow = service_for(profile)
    result = service.retrieve(principal, profile.customer_id, profile.currency)
    assert result.status == status
    assert result.long_term.count == count
    assert (result.long_term.amounts is None) == (count == 0)
    uow.commit.assert_not_called()


def test_absent_profile_is_uninitialized_without_creating_it(profile):
    service, principal, uow = service_for(profile)
    uow.profiles.get_revision.return_value = None
    view = service.retrieve(principal, profile.customer_id, "USD")
    assert view.status == BaselineStatus.UNINITIALIZED and view.version is None
    assert view.long_term.amounts is None and view.short_term.count == 0
    assert view.timezone == "Asia/Almaty"
    uow.profiles.save.assert_not_called()
    with pytest.raises(NotFound, match="revision"):
        service.retrieve(principal, profile.customer_id, "USD", version=1)


def test_unauthorized_read_never_opens_database(profile):
    def forbidden_factory():
        pytest.fail("unauthorized access opened storage")

    service = ProfileService(forbidden_factory)
    with pytest.raises(NotFound, match="customer not found"):
        service.retrieve(Principal(uuid4(), frozenset({Role.ANALYST})), profile.customer_id, "KZT")


def test_cutoff_and_version_validation(profile):
    service, principal, _ = service_for(profile)
    for kwargs in (
        {"as_of": profile.as_of},
        {"version": 0},
        {"as_of": profile.as_of.replace(tzinfo=None), "version": 1},
        {"as_of": profile.as_of + timedelta(days=2), "version": 1},
    ):
        with pytest.raises(ProfileQueryError):
            service.retrieve(principal, profile.customer_id, "KZT", **kwargs)
    with pytest.raises(ProfileHistoryUnavailable):
        service.retrieve(
            principal,
            profile.customer_id,
            "KZT",
            as_of=profile.as_of - timedelta(days=1),
            version=1,
        )


def test_candidate_instant_is_excluded_and_read_does_not_mutate(profile):
    candidate = replace(
        profile.observations[0],
        transaction_id=uuid4(),
        timestamp=profile.as_of,
        amount=Decimal("8000000"),
    )
    saved = replace(profile, observations=(*profile.observations, candidate))
    service, principal, uow = service_for(saved)
    view = service.retrieve(principal, profile.customer_id, "KZT", as_of=profile.as_of, version=1)
    assert view.long_term.count == 20 and view.long_term.amounts.median == Decimal("30000")
    assert len(saved.observations) == 21
    uow.commit.assert_not_called()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"minimum_history": 0},
        {"minimum_hour_count": 0},
        {"minimum_hour_share": Decimal("NaN")},
        {"minimum_hour_share": Decimal("0")},
        {"minimum_hour_share": Decimal("1.1")},
    ],
)
def test_invalid_descriptive_policy(kwargs):
    with pytest.raises(ValueError):
        ProfileReadPolicy(**kwargs)
