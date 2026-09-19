from typing import Protocol
from uuid import UUID

from backend.app.cases.entities import FraudCase
from backend.app.profile.entities import CustomerBehaviorProfile
from backend.app.shared.events import DomainEvent
from backend.app.transaction.entities import Transaction


class TransactionRepository(Protocol):
    def get(self, transaction_id: UUID) -> Transaction | None: ...
    def add(self, transaction: Transaction) -> None: ...


class CustomerProfileRepository(Protocol):
    def get(self, customer_id: UUID, currency: str) -> CustomerBehaviorProfile | None: ...
    def save(self, profile: CustomerBehaviorProfile, *, expected_version: int) -> None: ...


class FraudCaseRepository(Protocol):
    def get(self, case_id: UUID) -> FraudCase | None: ...
    def save(self, case: FraudCase) -> None: ...


class OutboxRepository(Protocol):
    def add(self, event: DomainEvent) -> None: ...


class UnitOfWork(Protocol):
    """Adapters must atomically commit business writes and outbox records."""

    transactions: TransactionRepository
    profiles: CustomerProfileRepository
    cases: FraudCaseRepository
    outbox: OutboxRepository

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
