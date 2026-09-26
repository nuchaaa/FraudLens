import hmac
from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request

from backend.adapters.security import CredentialRegistry
from backend.app.evaluation.contracts import EvaluationEngine
from backend.app.identity.service import IdentityService
from backend.app.shared.security import Principal
from backend.app.transaction.service import TransactionService, UnitOfWorkFactory


@dataclass(frozen=True)
class ApiServices:
    credentials: CredentialRegistry
    uow_factory: UnitOfWorkFactory | None
    experimental_enabled: bool = False
    evaluation_engine: EvaluationEngine | None = None
    identity: IdentityService | None = None
    human_origin: str | None = None
    secure_cookies: bool = True

    @property
    def cookie_prefix(self) -> str:
        return "__Host-fl_" if self.secure_cookies else "fl_"


def get_services(request: Request) -> ApiServices:
    return cast(ApiServices, request.app.state.services)


def authenticated_principal(
    request: Request,
    services: Annotated[ApiServices, Depends(get_services)],
) -> Principal:
    header = request.headers.get("Authorization")
    access = request.cookies.get(f"{services.cookie_prefix}access")
    refresh = request.cookies.get(f"{services.cookie_prefix}refresh")
    csrf = request.cookies.get(f"{services.cookie_prefix}csrf")
    if header is not None:
        if access or refresh or csrf:
            raise HTTPException(401, "mixed credentials are not accepted")
        scheme, _, token = header.partition(" ")
        principal = (
            services.credentials.authenticate(token)
            if scheme.lower() == "bearer" and token and " " not in token
            else None
        )
        if principal is not None:
            return principal
    elif services.identity is not None and access and csrf:
        session = services.identity.session(access, csrf)
        if session is not None:
            if request.method not in ("GET", "HEAD", "OPTIONS") and (
                request.headers.get("Origin") != services.human_origin
                or not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), session.csrf)
            ):
                raise HTTPException(403, "request origin or CSRF token invalid")
            return session.principal
    raise HTTPException(
        status_code=401,
        detail="valid credential required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def transaction_service(
    services: Annotated[ApiServices, Depends(get_services)],
    principal: Annotated[Principal, Depends(authenticated_principal)],
) -> TransactionService:
    if services.uow_factory is None:
        raise HTTPException(status_code=503, detail="transaction storage is not configured")
    return TransactionService(services.uow_factory)
