from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from backend.adapters.database.models import CustomerRow, TransactionRow
from backend.adapters.database.repository_base import Repository
from backend.app.features.context import ActivityHistoryLimit, FeatureInputError
from backend.app.profile.entities import Customer
from backend.app.shared.validation import currency_code, utc
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
    def history_before(
        self,
        customer_id: UUID,
        currency: str,
        *,
        since: datetime,
        before: datetime,
        exclude_transaction_id: UUID,
        limit: int,
    ) -> tuple[Transaction, ...]:
        currency_code(currency)
        since, before = utc(since), utc(before)
        if since >= before or limit < 1:
            raise FeatureInputError("invalid activity interval or row limit")
        # One PostgreSQL statement snapshot; event time is NOT an availability timestamp.
        rows = self.session.scalars(
            select(TransactionRow)
            .where(
                TransactionRow.customer_id == customer_id,
                TransactionRow.currency == currency,
                TransactionRow.timestamp > since,
                TransactionRow.timestamp < before,
                TransactionRow.transaction_id != exclude_transaction_id,
            )
            .order_by(TransactionRow.timestamp, TransactionRow.transaction_id)
            .limit(limit + 1)
        ).all()
        if len(rows) > limit:
            raise ActivityHistoryLimit("activity history exceeds the requested row limit")
        return tuple(transaction_from_row(row) for row in rows)

    def add(self, transaction: Transaction) -> None:
        self.session.add(TransactionRow(**asdict(transaction)))
        self.session.flush()

    def get(self, transaction_id: UUID) -> Transaction | None:
        row = self.session.get(TransactionRow, transaction_id)
        return transaction_from_row(row) if row else None
