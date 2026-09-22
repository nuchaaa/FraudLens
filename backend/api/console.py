import base64
import binascii
import json
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime, BaseModel

from backend.api.dependencies import ApiServices, authenticated_principal, get_services
from backend.api.transactions import TransactionResponse
from backend.app.cases.entities import CaseState
from backend.app.console.contracts import ConsoleSummary, WorklistCursor, WorklistItem
from backend.app.console.service import ConsoleService
from backend.app.shared.security import Principal
from backend.app.transaction.service import transaction_document

router = APIRouter(prefix="/api/v1/console", tags=["analyst console reads"])
type Auth = Annotated[Principal, Depends(authenticated_principal)]
type Services = Annotated[ApiServices, Depends(get_services)]


def service(services: Services) -> ConsoleService:
    if services.uow_factory is None:
        raise HTTPException(503, "console storage is not configured")
    return ConsoleService(services.uow_factory)


def encode_cursor(cursor: WorklistCursor) -> str:
    payload = json.dumps(
        {"timestamp": cursor.timestamp.isoformat(), "transaction_id": str(cursor.transaction_id)},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(value: str | None) -> WorklistCursor | None:
    if value is None:
        return None
    if not 1 <= len(value) <= 300:
        raise HTTPException(422, "invalid cursor")
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        document = json.loads(raw)
        if not isinstance(document, dict) or set(document) != {"timestamp", "transaction_id"}:
            raise ValueError
        timestamp = datetime.fromisoformat(document["timestamp"])
        if timestamp.tzinfo is None:
            raise ValueError
        return WorklistCursor(timestamp, UUID(document["transaction_id"]))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        raise HTTPException(422, "invalid cursor") from None


class WorklistResponseItem(BaseModel):
    transaction: TransactionResponse
    evaluation_id: UUID | None
    evaluation_created_at: AwareDatetime | None
    evaluation_status: str | None
    strategy: str | None
    score: float | None
    risk_level: str | None
    suggested_action: str | None
    case_id: UUID | None
    case_state: CaseState | None
    experimental: bool
    calibrated: bool | None
    production_eligible: bool

    @classmethod
    def from_domain(cls, item: WorklistItem) -> Self:
        return cls(
            transaction=TransactionResponse.model_validate(transaction_document(item.transaction)),
            evaluation_id=item.evaluation_id,
            evaluation_created_at=item.evaluation_created_at,
            evaluation_status=item.evaluation_status,
            strategy=item.strategy,
            score=item.score,
            risk_level=item.risk_level,
            suggested_action=item.suggested_action,
            case_id=item.case_id,
            case_state=item.case_state,
            experimental=item.evaluation_id is not None,
            calibrated=False if item.evaluation_id is not None else None,
            production_eligible=False,
        )


class WorklistResponse(BaseModel):
    items: tuple[WorklistResponseItem, ...]
    next_cursor: str | None


class SummaryResponse(BaseModel):
    as_of: AwareDatetime
    transaction_time_basis: str
    transactions: int
    transactions_today: int
    evaluated_transactions: int
    high_risk_transactions: int
    cases_awaiting_review: int
    confirmed_fraud_cases: int
    suspicious_amount: str
    production_model_status: str
    experimental_results_calibrated: bool = False

    @classmethod
    def from_domain(cls, value: ConsoleSummary) -> Self:
        return cls(
            as_of=value.as_of,
            transaction_time_basis="transaction event timestamps in UTC",
            transactions=value.transactions,
            transactions_today=value.transactions_today,
            evaluated_transactions=value.evaluated_transactions,
            high_risk_transactions=value.high_risk_transactions,
            cases_awaiting_review=value.cases_awaiting_review,
            confirmed_fraud_cases=value.confirmed_fraud_cases,
            suspicious_amount=format(Decimal(value.suspicious_amount), ".2f"),
            production_model_status=value.production_model_status,
        )


@router.get("/summary", response_model=SummaryResponse)
def get_summary(principal: Auth, services: Services, response: Response) -> SummaryResponse:
    response.headers["Cache-Control"] = "no-store"
    return SummaryResponse.from_domain(service(services).summary(principal))


@router.get("/worklist", response_model=WorklistResponse)
def get_worklist(
    principal: Auth,
    services: Services,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=300)] = None,
) -> WorklistResponse:
    page = service(services).worklist(principal, limit=limit, cursor=decode_cursor(cursor))
    response.headers["Cache-Control"] = "no-store"
    return WorklistResponse(
        items=tuple(WorklistResponseItem.from_domain(item) for item in page.items),
        next_cursor=encode_cursor(page.next_cursor) if page.next_cursor else None,
    )
