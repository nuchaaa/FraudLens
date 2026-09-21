from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import AwareDatetime, BaseModel

from backend.api.dependencies import ApiServices, authenticated_principal, get_services
from backend.app.profile.read_model import BaselineStatus, BehaviorWindow, ProfileView
from backend.app.profile.service import ProfileService
from backend.app.shared.security import Principal

router = APIRouter(prefix="/api/v1/customers", tags=["behavior profiles"])


def profile_service(
    services: Annotated[ApiServices, Depends(get_services)],
    principal: Annotated[Principal, Depends(authenticated_principal)],
) -> ProfileService:
    if services.uow_factory is None:
        raise HTTPException(status_code=503, detail="profile storage is not configured")
    return ProfileService(services.uow_factory)


class AmountResponse(BaseModel):
    count: int
    median: str
    mad: str
    p95: str
    mean: str


class WindowResponse(BaseModel):
    days: int
    count: int
    amounts: AmountResponse | None
    observations_per_day: str
    local_hour_counts: tuple[int, ...]
    typical_local_hours: tuple[int, ...]
    known_recipients: tuple[UUID, ...]

    @classmethod
    def from_domain(cls, window: BehaviorWindow) -> Self:
        amounts = None
        if window.amounts is not None:
            amounts = AmountResponse(
                count=window.amounts.count,
                median=str(window.amounts.median),
                mad=str(window.amounts.mad),
                p95=str(window.amounts.p95),
                mean=str(window.amounts.mean),
            )
        return cls(
            **{
                **asdict(window),
                "amounts": amounts,
                "observations_per_day": str(window.observations_per_day),
            },
        )


class ProfileResponse(BaseModel):
    customer_id: UUID
    currency: str
    as_of: datetime
    version: int | None
    revision_as_of: datetime | None
    timezone: str
    status: BaselineStatus
    read_policy_version: str
    minimum_history: int
    history_source: Literal["repository_admissions"] = "repository_admissions"
    admission_workflow_verified: bool
    admission_policy_version: str | None
    learning_decision_id: UUID | None
    long_term: WindowResponse
    short_term: WindowResponse

    @classmethod
    def from_domain(cls, view: ProfileView) -> Self:
        return cls(
            customer_id=view.customer_id,
            currency=view.currency,
            as_of=view.as_of,
            version=view.version,
            revision_as_of=view.revision_as_of,
            timezone=view.timezone,
            status=view.status,
            read_policy_version=view.policy.version,
            minimum_history=view.policy.minimum_history,
            admission_workflow_verified=view.admission_workflow_verified,
            admission_policy_version=view.admission_policy_version,
            learning_decision_id=view.learning_decision_id,
            long_term=WindowResponse.from_domain(view.long_term),
            short_term=WindowResponse.from_domain(view.short_term),
        )


@router.get("/{customer_id}/profiles/{currency}", response_model=ProfileResponse)
def get_profile(
    customer_id: UUID,
    currency: Annotated[str, Path(pattern=r"^[A-Z]{3}$")],
    principal: Annotated[Principal, Depends(authenticated_principal)],
    service: Annotated[ProfileService, Depends(profile_service)],
    as_of: Annotated[AwareDatetime | None, Query()] = None,
    version: Annotated[int | None, Query(ge=1)] = None,
) -> ProfileResponse:
    return ProfileResponse.from_domain(
        service.retrieve(principal, customer_id, currency, as_of=as_of, version=version)
    )
