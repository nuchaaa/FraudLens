import hashlib
from dataclasses import asdict
from uuid import UUID

from sqlalchemy import text

from backend.adapters.database.models import IdempotencyRow
from backend.adapters.database.repository_base import Repository
from backend.app.shared.errors import HistoryConflict, IdempotencyConflict
from backend.app.transaction.idempotency import IdempotencyRecord


class PostgresIdempotencyRepository(Repository):
    def get(self, principal_id: UUID, key: str) -> IdempotencyRecord | None:
        row = self.session.get(IdempotencyRow, (principal_id, key), populate_existing=True)
        return (
            IdempotencyRecord(
                row.principal_id,
                row.key,
                row.request_sha256,
                row.transaction_id,
                row.response_json,
                row.status_code,
                row.created_at,
            )
            if row
            else None
        )

    def acquire(
        self, principal_id: UUID, key: str, request_sha256: str
    ) -> IdempotencyRecord | None:
        """Call BEFORE business writes. Serializes equal scoped keys until commit/rollback."""
        digest = hashlib.sha256(principal_id.bytes + key.encode("utf-8")).digest()
        lock_id = int.from_bytes(digest[:8], "big", signed=True)
        self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        record = self.get(principal_id, key)
        if record is not None and record.request_sha256 != request_sha256:
            raise IdempotencyConflict("idempotency key was already used with a different request")
        return record

    def add(self, record: IdempotencyRecord) -> None:
        existing = self.acquire(record.principal_id, record.key, record.request_sha256)
        if existing is not None:
            if existing != record:
                raise HistoryConflict("completed idempotent response cannot be replaced")
            return
        self.session.add(IdempotencyRow(**asdict(record)))
        self.session.flush()
