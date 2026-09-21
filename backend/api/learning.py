"""Independent administrative authorization for experimental profile learning."""

import json
from typing import Annotated, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.api.dependencies import ApiServices, authenticated_principal, get_services
from backend.api.evaluations import key_header, require_storage
from backend.app.profile.learning import ProfileLearningService
from backend.app.shared.security import Principal
from backend.app.transaction.service import SubmissionResult

router = APIRouter(prefix="/api/v1/experimental/profile-learning", tags=["profile learning"])
type Auth = Annotated[Principal, Depends(authenticated_principal)]
type Services = Annotated[ApiServices, Depends(get_services)]


class CaseLearningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: UUID
    expected_profile_version: int | None = Field(default=None, ge=1)


class BootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_ids: tuple[UUID, ...] = Field(min_length=5, max_length=100)

    @model_validator(mode="after")
    def unique_cases(self) -> Self:
        if len(set(self.case_ids)) != len(self.case_ids):
            raise ValueError("case IDs must be unique")
        return self


def learning_response(result: SubmissionResult) -> Response:
    identifier = json.loads(result.response_json)["decision_id"]
    return Response(
        result.response_json,
        result.status_code,
        media_type="application/json",
        headers={
            "Idempotency-Replayed": str(result.replayed).lower(),
            "Location": f"/api/v1/experimental/profile-learning/decisions/{identifier}",
        },
    )


@router.post("/case", status_code=201)
def apply_case(
    payload: CaseLearningRequest,
    principal: Auth,
    services: Services,
    key: Annotated[str, Depends(key_header)],
) -> Response:
    require_storage(services, write=True)
    assert services.uow_factory is not None
    return learning_response(
        ProfileLearningService(services.uow_factory).apply_case(
            principal,
            key,
            payload.case_id,
            expected_profile_version=payload.expected_profile_version,
        )
    )


@router.post("/bootstrap", status_code=201)
def bootstrap(
    payload: BootstrapRequest,
    principal: Auth,
    services: Services,
    key: Annotated[str, Depends(key_header)],
) -> Response:
    require_storage(services, write=True)
    assert services.uow_factory is not None
    return learning_response(
        ProfileLearningService(services.uow_factory).bootstrap(principal, key, payload.case_ids)
    )


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: UUID, principal: Auth, services: Services) -> Response:
    require_storage(services)
    assert services.uow_factory is not None
    decision = ProfileLearningService(services.uow_factory).retrieve(principal, decision_id)
    return Response(decision.response_json, media_type="application/json")
