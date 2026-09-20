from dataclasses import asdict
from uuid import UUID

from backend.adapters.database.models import CustomerRow, TransactionRow
from backend.adapters.database.repository_base import Repository
from backend.app.profile.entities import Customer
from backend.app.transaction.entities import Channel, Transaction, TransactionStatus


class PostgresCustomerRepository(Repository):
    def add(self, customer: Customer) -> None:
        self.session.add(CustomerRow(**asdict(customer)))
        self.session.flush()

    def get(self, customer_id: UUID) -> Customer | None:
        row = self.session.get(CustomerRow, customer_id)
        return Customer(row.customer_id, row.created_at, row.timezone) if row else None


def transaction_from_row(row: TransactionRow) -> Transaction:
    return Transaction(
        row.transaction_id,
        row.customer_id,
        row.recipient_id,
        row.amount,
        row.currency,
        row.timestamp,
        Channel(row.channel),
        row.device_id,
        TransactionStatus(row.status),
    )


class PostgresTransactionRepository(Repository):
    def add(self, transaction: Transaction) -> None:
        self.session.add(TransactionRow(**asdict(transaction)))
        self.session.flush()

    def get(self, transaction_id: UUID) -> Transaction | None:
        row = self.session.get(TransactionRow, transaction_id)
        return transaction_from_row(row) if row else None
