from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from backend.api.dependencies import authenticated_principal, transaction_service
from backend.app.shared.security import Principal
from backend.app.shared.validation import utc
from backend.app.transaction.entities import Channel, Transaction, TransactionStatus
from backend.app.transaction.service import (
    TransactionService,
    transaction_document,
    validate_idempotency_key,
)

router = APIRouter(prefix="/api/v1", tags=["synthetic transactions"])
type Authenticated = Annotated[Principal, Depends(authenticated_principal)]
type Service = Annotated[TransactionService, Depends(transaction_service)]


class TransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: UUID
    customer_id: UUID
    recipient_id: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    timestamp: AwareDatetime
    channel: Channel
    device_id: str = Field(min_length=1, max_length=200)

    @field_validator("amount", mode="before", json_schema_input_type=str)
    @classmethod
    def amount_is_decimal_string(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("amount must be a decimal string, e.g. '30000.00'")
        return value

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_is_iso_string(cls, value: object) -> object:
        if not isinstance(value, str) or "T" not in value:
            raise ValueError("timestamp must be an ISO 8601 string with timezone")
        return value

    @field_validator("timestamp")
    @classmethod
    def timestamp_fits_utc(cls, value: datetime) -> datetime:
        try:
            utc(value)
        except OverflowError:
            raise ValueError("timestamp is outside the supported UTC range") from None
        return value

    @field_validator("device_id")
    @classmethod
    def device_is_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("device_id must not be blank")
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("device_id must not contain control characters")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("device_id must be valid UTF-8 text") from None
        return value

    def to_domain(self) -> Transaction:
        return Transaction(**self.model_dump())


class TransactionResponse(BaseModel):
    transaction_id: UUID
    customer_id: UUID
    recipient_id: UUID
    amount: str
    currency: str
    timestamp: AwareDatetime
    channel: Channel
    device_id: str
    status: TransactionStatus


class CustomerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: UUID
    timezone: str = Field(default="Asia/Almaty", min_length=1, max_length=100)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("timezone must be a known IANA timezone") from None
        return value


class CustomerResponse(BaseModel):
    customer_id: UUID
    created_at: AwareDatetime
    timezone: str


@router.post("/transactions", status_code=201, response_model=TransactionResponse)
def submit_transaction(
    body: TransactionRequest,
    principal: Authenticated,
    service: Service,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=200)],
) -> Response:
    try:
        validate_idempotency_key(idempotency_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    result = service.submit(principal, idempotency_key, body.to_domain())
    return Response(
        content=result.response_json,
        status_code=result.status_code,
        media_type="application/json",
        headers={
            "Location": f"/api/v1/transactions/{body.transaction_id}",
            "Idempotency-Replayed": str(result.replayed).lower(),
            "Cache-Control": "no-store",
        },
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: UUID,
    principal: Authenticated,
    service: Service,
    response: Response,
) -> dict[str, str]:
    response.headers["Cache-Control"] = "no-store"
    return transaction_document(service.retrieve(principal, transaction_id))


@router.post("/customers", status_code=201, response_model=CustomerResponse)
def enroll_customer(
    body: CustomerRequest,
    principal: Authenticated,
    service: Service,
    response: Response,
) -> CustomerResponse:
    customer = service.enroll_customer(principal, body.customer_id, body.timezone)
    response.headers["Cache-Control"] = "no-store"
    return CustomerResponse(
        customer_id=customer.customer_id,
        created_at=customer.created_at,
        timezone=customer.timezone,
    )
