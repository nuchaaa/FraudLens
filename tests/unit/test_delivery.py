import pytest

from backend.app.shared.delivery import DeliveryPolicy, dispatch


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lease_seconds": 0},
        {"lease_seconds": 3601},
        {"max_attempts": 0},
        {"max_attempts": 101},
        {"retry_seconds": 0},
        {"retry_seconds": 3601},
        {"max_retry_seconds": 86401},
    ],
)
def test_invalid_delivery_policy(kwargs):
    with pytest.raises(ValueError):
        DeliveryPolicy(**kwargs)


def test_exponential_backoff_has_cap():
    policy = DeliveryPolicy()
    assert [policy.delay(i) for i in (1, 2, 3, 100)] == [5, 10, 20, 3600]


@pytest.mark.parametrize("limit", [0, 1001])
def test_dispatch_rejects_unbounded_batches(limit):
    with pytest.raises(ValueError):
        dispatch(None, None, limit=limit)
