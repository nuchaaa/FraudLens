from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from backend.app.shared.validation import currency_code, nonempty, positive_amount, utc


class Channel(StrEnum):
    MOBILE = "MOBILE"
    WEB = "WEB"
    ATM = "ATM"
    BRANCH = "BRANCH"


class TransactionStatus(StrEnum):
    RECEIVED = "RECEIVED"
    EVALUATED = "EVALUATED"


@dataclass(frozen=True)
class Transaction:
    transaction_id: UUID
    customer_id: UUID
    recipient_id: UUID
    amount: Decimal
    currency: str
    timestamp: datetime
    channel: Channel
    device_id: str
    status: TransactionStatus = TransactionStatus.RECEIVED

    def __post_init__(self) -> None:
        positive_amount(self.amount)
        currency_code(self.currency)
        nonempty(self.device_id, "device_id")
        object.__setattr__(self, "timestamp", utc(self.timestamp))
