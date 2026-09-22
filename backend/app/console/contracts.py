from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from backend.app.cases.entities import CaseState
from backend.app.transaction.entities import Transaction


@dataclass(frozen=True)
class WorklistCursor:
    timestamp: datetime
    transaction_id: UUID


@dataclass(frozen=True)
class WorklistItem:
    transaction: Transaction
    evaluation_id: UUID | None
    evaluation_created_at: datetime | None
    evaluation_status: str | None
    strategy: str | None
    score: float | None
    risk_level: str | None
    suggested_action: str | None
    case_id: UUID | None
    case_state: CaseState | None


@dataclass(frozen=True)
class WorklistPage:
    items: tuple[WorklistItem, ...]
    next_cursor: WorklistCursor | None


@dataclass(frozen=True)
class ConsoleSummary:
    as_of: datetime
    transactions: int
    transactions_today: int
    evaluated_transactions: int
    high_risk_transactions: int
    cases_awaiting_review: int
    confirmed_fraud_cases: int
    suspicious_amount: Decimal
    production_model_status: str = "NO_PRODUCTION_MODEL"


class ConsoleRepository(Protocol):
    def worklist(
        self,
        customer_ids: frozenset[UUID] | None,
        *,
        limit: int,
        cursor: WorklistCursor | None,
    ) -> WorklistPage: ...

    def summary(
        self, customer_ids: frozenset[UUID] | None, *, as_of: datetime
    ) -> ConsoleSummary: ...
