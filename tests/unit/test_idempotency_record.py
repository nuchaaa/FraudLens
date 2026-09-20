from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.app.transaction.idempotency import IdempotencyRecord


@pytest.mark.parametrize(
    "change",
    [
        {"key": ""},
        {"key": " padded"},
        {"key": "a" * 201},
        {"request_sha256": "bad"},
        {"status_code": 500},
        {"response_json": "invalid"},
        {"response_json": "[]"},
        {"created_at": datetime(2026, 9, 19)},
    ],
)
def test_invalid_idempotency_record(change):
    record = IdempotencyRecord(uuid4(), "key", "a" * 64, uuid4(), "{}", 201, datetime.now(UTC))
    with pytest.raises(ValueError):
        replace(record, **change)
