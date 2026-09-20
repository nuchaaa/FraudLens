import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.app.audit.entities import AuditEvent
from backend.app.profile.entities import Customer
from backend.app.shared.errors import DuplicateCustomer, DuplicateTransaction
from backend.app.shared.events import DomainEvent, EventType
from backend.app.shared.ports import UnitOfWork
from backend.app.shared.security import Forbidden, NotFound, Principal, Role
from backend.app.transaction.entities import Transaction, TransactionStatus
from backend.app.transaction.idempotency import IdempotencyRecord

type UnitOfWorkFactory = Callable[[], UnitOfWork]


def transaction_document(transaction: Transaction) -> dict[str, str]:
    return {
        "transaction_id": str(transaction.transaction_id),
        "customer_id": str(transaction.customer_id),
        "recipient_id": str(transaction.recipient_id),
        "amount": format(transaction.amount, ".2f"),
        "currency": transaction.currency,
        "timestamp": transaction.timestamp.isoformat(),
        "channel": transaction.channel.value,
        "device_id": transaction.device_id,
        "status": transaction.status.value,
    }


def canonical_request_digest(transaction: Transaction) -> str:
    # Version the operation as well as the canonical format. Future routes must not
    # accidentally replay an unrelated response in the same principal/key namespace.
    body = json.dumps(transaction_document(transaction), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(("submit-transaction:v1\n" + body).encode()).hexdigest()


def validate_idempotency_key(key: str) -> str:
    if not re.fullmatch(r"[\x21-\x7e]{1,200}", key):
        raise ValueError("Idempotency-Key must contain 1-200 printable ASCII characters, no spaces")
    return key


@dataclass(frozen=True)
class SubmissionResult:
    response_json: str
    status_code: int
    replayed: bool


class TransactionService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self.uow_factory = uow_factory

    def submit(self, principal: Principal, key: str, transaction: Transaction) -> SubmissionResult:
        if not principal.can_submit(transaction.customer_id):
            raise Forbidden("submission is not permitted for this customer")
        if transaction.status != TransactionStatus.RECEIVED:
            raise ValueError("new transactions must have RECEIVED status")
        validate_idempotency_key(key)
        digest = canonical_request_digest(transaction)
        with self.uow_factory() as uow:
            # Authorization precedes replay. The lock precedes ALL business writes.
            prior = uow.idempotency.acquire(principal.principal_id, key, digest)
            if prior is not None:
                return SubmissionResult(prior.response_json, prior.status_code, True)
            if uow.customers.get(transaction.customer_id) is None:
                raise NotFound("customer not found")
            if uow.transactions.get(transaction.transaction_id) is not None:
                raise DuplicateTransaction("transaction ID already exists")
            received_at = datetime.now(UTC)
            correlation_id = uuid4()
            response = json.dumps(
                transaction_document(transaction), sort_keys=True, separators=(",", ":")
            )
            uow.transactions.add(transaction)
            uow.audit.add(
                AuditEvent(
                    uuid4(),
                    principal.principal_id,
                    "transaction.submitted",
                    transaction.transaction_id,
                    correlation_id,
                    received_at,
                    "Synthetic transaction received; risk evaluation pending.",
                )
            )
            uow.outbox.add(
                DomainEvent(
                    uuid4(),
                    EventType.TRANSACTION_RECEIVED,
                    transaction.transaction_id,
                    received_at,
                    correlation_id,
                    (("customer_id", str(transaction.customer_id)),),
                )
            )
            uow.idempotency.add(
                IdempotencyRecord(
                    principal.principal_id,
                    key,
                    digest,
                    transaction.transaction_id,
                    response,
                    201,
                    received_at,
                )
            )
            uow.commit()
            return SubmissionResult(response, 201, False)

    def retrieve(self, principal: Principal, transaction_id: UUID) -> Transaction:
        with self.uow_factory() as uow:
            transaction = uow.transactions.get(transaction_id)
            if transaction is None or not principal.can_read(transaction.customer_id):
                raise NotFound("transaction not found")
            return transaction

    def enroll_customer(self, principal: Principal, customer_id: UUID, timezone: str) -> Customer:
        if Role.ADMIN not in principal.roles:
            raise Forbidden("customer enrollment requires admin role")
        customer = Customer(customer_id, datetime.now(UTC), timezone)
        with self.uow_factory() as uow:
            if uow.customers.get(customer_id) is not None:
                raise DuplicateCustomer("customer ID already exists")
            uow.customers.add(customer)
            uow.audit.add(
                AuditEvent(
                    uuid4(),
                    principal.principal_id,
                    "customer.enrolled",
                    customer_id,
                    uuid4(),
                    customer.created_at,
                    "Synthetic customer enrolled; no trusted profile observations created.",
                )
            )
            uow.commit()
        return customer
