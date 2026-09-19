import math
import re
from datetime import UTC, datetime
from decimal import Decimal


def nonempty(value: str, name: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be blank")


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(UTC)


def currency_code(value: str) -> None:
    if not re.fullmatch(r"[A-Z]{3}", value):
        raise ValueError("currency must be a three-letter uppercase code")


def probability(value: float) -> None:
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("score must be finite and between 0 and 1")


def positive_amount(value: Decimal) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError("amount must be a finite positive Decimal")
    if value > Decimal("9999999999999999.99") or value != value.quantize(Decimal("0.01")):
        raise ValueError("amount must fit NUMERIC(18,2)")
