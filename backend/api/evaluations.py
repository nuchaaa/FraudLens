"""Opt-in experimental evaluations and analyst review; no model uploads or actions."""

import json
from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.api.dependencies import ApiServices, authenticated_principal, get_services
from backend.app.evaluation.service import EvaluationService, ReviewService
from backend.app.feedback.entities import AnalystVerdict
from backend.app.risk.service import Strategy
from backend.app.shared.security import Principal
from backend.app.transaction.service import SubmissionResult, validate_idempotency_key

router = APIRouter(prefix="/api/v1/experimental", tags=["experimental evaluations and review"])
type Auth = Annotated[Principal, Depends(authenticated_principal)]
type Services = Annotated[ApiServices, Depends(get_services)]


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: UUID
    profile_version: int | None = Field(ge=1)
    strategy: Strategy
    manifest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def model_contract(self) -> Self:
        if (self.strategy == Strategy.RULES_ONLY) != (self.manifest_sha256 is None):
            raise ValueError(
                "model strategies require an explicit manifest digest; rules-only forbids it"
            )
        return self


class CaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evaluation_id: UUID


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    action: Literal["start_review", "close", "feedback"]
    verdict: AnalystVerdict | None = None
    comment: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def feedback_contract(self) -> Self:
        if self.action == "feedback":
            if self.verdict is None or self.comment is None or not self.comment.strip():
                raise ValueError("feedback requires verdict and nonblank comment")
        elif self.verdict is not None or self.comment is not None:
            raise ValueError("only feedback accepts verdict/comment")
        return self


def key_header(key: Annotated[str, Header(alias="Idempotency-Key")]) -> str:
    try:
        return validate_idempotency_key(key)
    except ValueError:
        raise HTTPException(422, "invalid Idempotency-Key") from None


def require_storage(services: ApiServices, *, write: bool = False) -> None:
    if services.uow_factory is None:
        raise HTTPException(503, "evaluation storage is not configured")
    if write and not services.experimental_enabled:
        raise HTTPException(503, "experimental writes are disabled")


def result_response(result: SubmissionResult, collection: str, id_field: str) -> Response:
    identifier = json.loads(result.response_json)[id_field]
    return Response(
        result.response_json,
        result.status_code,
        media_type="application/json",
        headers={
            "Idempotency-Replayed": str(result.replayed).lower(),
            "Location": f"/api/v1/experimental/{collection}/{identifier}",
        },
    )


@router.post("/evaluations", status_code=201)
def evaluate(
    payload: EvaluationRequest,
    principal: Auth,
    services: Services,
    key: Annotated[str, Depends(key_header)],
) -> Response:
    require_storage(services, write=True)
    assert services.uow_factory is not None and services.evaluation_engine is not None
    result = EvaluationService(services.uow_factory, services.evaluation_engine).submit(
        principal, key, **payload.model_dump()
    )
    return result_response(result, "evaluations", "evaluation_id")


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: UUID, principal: Auth, services: Services) -> Response:
    require_storage(services)
    assert services.uow_factory is not None and services.evaluation_engine is not None
    record = EvaluationService(services.uow_factory, services.evaluation_engine).retrieve(
        principal, evaluation_id
    )
    return Response(record.response_json, media_type="application/json")


@router.post("/cases", status_code=201)
def create_case(
    payload: CaseRequest,
    principal: Auth,
    services: Services,
    key: Annotated[str, Depends(key_header)],
) -> Response:
    require_storage(services, write=True)
    assert services.uow_factory is not None
    return result_response(
        ReviewService(services.uow_factory).create(principal, key, payload.evaluation_id),
        "cases",
        "case_id",
    )


@router.get("/cases/{case_id}")
def get_case(case_id: UUID, principal: Auth, services: Services) -> Response:
    require_storage(services)
    assert services.uow_factory is not None
    return Response(
        ReviewService(services.uow_factory).retrieve(principal, case_id),
        media_type="application/json",
    )


@router.post("/cases/{case_id}/review")
def review_case(
    case_id: UUID,
    payload: ReviewRequest,
    principal: Auth,
    services: Services,
    key: Annotated[str, Depends(key_header)],
) -> Response:
    require_storage(services, write=True)
    assert services.uow_factory is not None
    result = ReviewService(services.uow_factory).change(
        principal, key, case_id, **payload.model_dump()
    )
    return result_response(result, "cases", "case_id")
