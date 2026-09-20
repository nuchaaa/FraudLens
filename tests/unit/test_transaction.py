from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from backend.app.transaction.entities import Transaction


@pytest.mark.parametrize("amount", ["0", "-1", "NaN", "Infinity", "0.001", "10000000000000000"])
def test_invalid_money(transaction: Transaction, amount: str) -> None:
    with pytest.raises(ValueError):
        replace(transaction, amount=Decimal(amount))


def test_binary_float_money_rejected(transaction: Transaction) -> None:
    with pytest.raises(ValueError):
        replace(transaction, amount=30.1)


@pytest.mark.parametrize("currency", ["kzt", "KZ", "KZT ", "123", ""])
def test_currency_validation(transaction: Transaction, currency: str) -> None:
    with pytest.raises(ValueError):
        replace(transaction, currency=currency)


def test_naive_time_rejected(transaction: Transaction) -> None:
    with pytest.raises(ValueError, match="timezone"):
        replace(transaction, timestamp=datetime(2026, 9, 19))


def test_timestamps_normalize_to_utc(transaction: Transaction) -> None:
    local = transaction.timestamp.astimezone(timezone(timedelta(hours=5)))
    normalized = replace(transaction, timestamp=local)
    assert normalized.timestamp.isoformat().endswith("+00:00")
    assert normalized.timestamp == transaction.timestamp


def test_transaction_immutable(transaction: Transaction) -> None:
    with pytest.raises(FrozenInstanceError):
        transaction.amount = Decimal("1")  # type: ignore[misc]


@pytest.mark.parametrize("device_id", ["  ", "x" * 201, "device\u0000", "device\n"])
def test_invalid_device_rejected(transaction: Transaction, device_id: str) -> None:
    with pytest.raises(ValueError):
        replace(transaction, device_id=device_id)
