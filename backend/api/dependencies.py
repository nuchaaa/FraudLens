from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.adapters.security import CredentialRegistry
from backend.app.evaluation.contracts import EvaluationEngine
from backend.app.shared.security import Principal
from backend.app.transaction.service import TransactionService, UnitOfWorkFactory

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ApiServices:
    credentials: CredentialRegistry
    uow_factory: UnitOfWorkFactory | None
    experimental_enabled: bool = False
    evaluation_engine: EvaluationEngine | None = None


def get_services(request: Request) -> ApiServices:
    return cast(ApiServices, request.app.state.services)


def authenticated_principal(
    services: Annotated[ApiServices, Depends(get_services)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    principal = services.credentials.authenticate(credentials.credentials) if credentials else None
    if principal is None:
        raise HTTPException(
            status_code=401,
            detail="valid bearer credential required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def transaction_service(
    services: Annotated[ApiServices, Depends(get_services)],
    principal: Annotated[Principal, Depends(authenticated_principal)],
) -> TransactionService:
    if services.uow_factory is None:
        raise HTTPException(status_code=503, detail="transaction storage is not configured")
    return TransactionService(services.uow_factory)
