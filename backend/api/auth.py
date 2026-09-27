"""Opt-in browser login; opaque tokens live only in HttpOnly cookies."""

import base64
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, SecretStr

from backend.api.dependencies import ApiServices, get_services
from backend.app.identity.policy import IssuedSecrets
from backend.app.identity.service import AuthenticationDenied, HumanSession, IdentityService

router = APIRouter(prefix="/api/v1/auth", tags=["human sessions"])
type Services = Annotated[ApiServices, Depends(get_services)]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login: str
    password: SecretStr


class MfaResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID
    credential: dict[str, object]


class FirstFactorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr


class RemoveFactorRequest(FirstFactorRequest):
    credential_id: str


def _identity(services: ApiServices) -> IdentityService:
    if services.identity is None:
        raise HTTPException(503, "human authentication is not configured")
    return services.identity


def _origin(request: Request, services: ApiServices, *, json_body: bool = False) -> None:
    if request.headers.get("Origin") != services.human_origin:
        raise HTTPException(403, "request origin invalid")
    if (
        json_body
        and request.headers.get("Content-Type", "").split(";")[0].strip().lower()
        != "application/json"
    ):
        raise HTTPException(415, "JSON content type required")
    if request.headers.get("Authorization") is not None:
        raise HTTPException(401, "mixed credentials are not accepted")


def _cookies(response: Response, services: ApiServices, issued: IssuedSecrets) -> None:
    for name, value in (
        ("access", issued.access),
        ("refresh", issued.refresh),
        ("csrf", issued.csrf),
    ):
        response.set_cookie(
            f"{services.cookie_prefix}{name}",
            value,
            max_age=300 if name == "access" else 28800,
            path="/",
            secure=services.secure_cookies,
            httponly=True,
            samesite="strict",
        )


def _clear(response: Response, services: ApiServices) -> None:
    for name in ("access", "refresh", "csrf"):
        response.delete_cookie(
            f"{services.cookie_prefix}{name}",
            path="/",
            secure=services.secure_cookies,
            httponly=True,
            samesite="strict",
        )


def _session_document(session: HumanSession) -> dict[str, object]:
    return {
        "account_id": str(session.account_id),
        "role": next(iter(session.principal.roles)).value,
        "customer_ids": sorted(str(item) for item in session.principal.customer_ids),
        "csrf": session.csrf,
    }


@router.post("/login")
def login(
    body: LoginRequest, request: Request, response: Response, services: Services
) -> dict[str, object]:
    identity = _identity(services)
    _origin(request, services, json_body=True)
    try:
        issued = identity.login(body.login, body.password.get_secret_value())
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    _cookies(response, services, issued)
    session = identity.session(issued.access, issued.csrf)
    assert session is not None
    return _session_document(session)


@router.post("/mfa/login/options")
def mfa_login_options(
    body: LoginRequest, request: Request, services: Services
) -> dict[str, object]:
    identity = _identity(services)
    _origin(request, services, json_body=True)
    try:
        result = identity.start_mfa_login(body.login, body.password.get_secret_value())
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    return {"challenge_id": str(result.challenge_id), "public_key": result.options}


@router.post("/mfa/login/verify")
def mfa_login_verify(
    body: MfaResponseRequest, request: Request, response: Response, services: Services
) -> dict[str, object]:
    identity = _identity(services)
    _origin(request, services, json_body=True)
    try:
        issued = identity.finish_mfa_login(body.challenge_id, body.credential)
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    _cookies(response, services, issued)
    current = identity.session(issued.access, issued.csrf)
    assert current is not None
    return _session_document(current)


@router.post("/mfa/first-factor/options")
def first_factor_options(
    body: FirstFactorRequest, request: Request, services: Services
) -> dict[str, object]:
    identity = _identity(services)
    _origin(request, services, json_body=True)
    try:
        result = identity.start_first_factor(
            request.cookies.get(f"{services.cookie_prefix}access", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
            request.headers.get("X-CSRF-Token", ""),
            body.password.get_secret_value(),
        )
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    return {"challenge_id": str(result.challenge_id), "public_key": result.options}


@router.post("/mfa/first-factor/verify", status_code=201)
def first_factor_verify(
    body: MfaResponseRequest, request: Request, response: Response, services: Services
) -> dict[str, bool]:
    identity = _identity(services)
    _origin(request, services, json_body=True)
    try:
        identity.finish_first_factor(
            request.cookies.get(f"{services.cookie_prefix}access", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
            request.headers.get("X-CSRF-Token", ""),
            body.challenge_id,
            body.credential,
        )
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    _clear(response, services)
    return {"enrolled": True}


@router.post("/mfa/add-factor/options")
def add_factor_options(
    body: FirstFactorRequest, request: Request, services: Services
) -> dict[str, object]:
    identity = _identity(services)
    _origin(request, services, json_body=True)
    try:
        result = identity.start_add_factor(
            request.cookies.get(f"{services.cookie_prefix}access", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
            request.headers.get("X-CSRF-Token", ""),
            body.password.get_secret_value(),
        )
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    return {"challenge_id": str(result.challenge_id), "public_key": result.options}


@router.post("/mfa/add-factor/proof")
def add_factor_proof(
    body: MfaResponseRequest, request: Request, services: Services
) -> dict[str, object]:
    identity = _identity(services)
    _origin(request, services, json_body=True)
    try:
        result = identity.finish_add_factor_proof(
            request.cookies.get(f"{services.cookie_prefix}access", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
            request.headers.get("X-CSRF-Token", ""),
            body.challenge_id,
            body.credential,
        )
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    return {"challenge_id": str(result.challenge_id), "public_key": result.options}


@router.post("/mfa/add-factor/verify", status_code=201)
def add_factor_verify(
    body: MfaResponseRequest, request: Request, response: Response, services: Services
) -> dict[str, bool]:
    identity = _identity(services)
    _origin(request, services, json_body=True)
    try:
        identity.finish_add_factor(
            request.cookies.get(f"{services.cookie_prefix}access", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
            request.headers.get("X-CSRF-Token", ""),
            body.challenge_id,
            body.credential,
        )
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    _clear(response, services)
    return {"enrolled": True}


@router.get("/mfa/factors")
def factors(request: Request, services: Services) -> dict[str, object]:
    identity = _identity(services)
    if request.headers.get("Authorization") is not None:
        raise HTTPException(401, "mixed credentials are not accepted")
    try:
        credentials = identity.list_factors(
            request.cookies.get(f"{services.cookie_prefix}access", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
        )
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    return {
        "items": [
            {
                "credential_id": base64.urlsafe_b64encode(item.credential_id).rstrip(b"=").decode(),
                "created_at": item.created_at.isoformat(),
                "last_used_at": item.last_used_at.isoformat() if item.last_used_at else None,
                "device_type": item.device_type,
                "backed_up": item.backed_up,
            }
            for item in credentials
        ]
    }


@router.post("/mfa/remove-factor/options")
def remove_factor_options(
    body: RemoveFactorRequest, request: Request, services: Services
) -> dict[str, object]:
    identity = _identity(services)
    _origin(request, services, json_body=True)
    try:
        result = identity.start_remove_factor(
            request.cookies.get(f"{services.cookie_prefix}access", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
            request.headers.get("X-CSRF-Token", ""),
            body.password.get_secret_value(),
            body.credential_id,
        )
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    return {"challenge_id": str(result.challenge_id), "public_key": result.options}


@router.post("/mfa/remove-factor/verify")
def remove_factor_verify(
    body: MfaResponseRequest, request: Request, response: Response, services: Services
) -> dict[str, bool]:
    identity = _identity(services)
    _origin(request, services, json_body=True)
    try:
        identity.finish_remove_factor(
            request.cookies.get(f"{services.cookie_prefix}access", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
            request.headers.get("X-CSRF-Token", ""),
            body.challenge_id,
            body.credential,
        )
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    _clear(response, services)
    return {"removed": True}


@router.get("/session")
def session(request: Request, services: Services) -> dict[str, object]:
    identity = _identity(services)
    if request.headers.get("Authorization") is not None:
        raise HTTPException(401, "mixed credentials are not accepted")
    current = identity.session(
        request.cookies.get(f"{services.cookie_prefix}access", ""),
        request.cookies.get(f"{services.cookie_prefix}csrf", ""),
    )
    if current is None:
        pending = identity.pending_refresh(
            request.cookies.get(f"{services.cookie_prefix}refresh", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
        )
        if pending is None:
            raise HTTPException(401, "valid credential required")
        return {"refresh_required": True, "csrf": pending}
    return _session_document(current)


@router.post("/refresh")
def refresh(request: Request, response: Response, services: Services) -> dict[str, object]:
    identity = _identity(services)
    _origin(request, services)
    try:
        issued = identity.refresh(
            request.cookies.get(f"{services.cookie_prefix}refresh", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
            request.headers.get("X-CSRF-Token", ""),
        )
    except AuthenticationDenied:
        _clear(response, services)
        response.status_code = 401
        return {"detail": "invalid credentials"}
    _cookies(response, services, issued)
    current = identity.session(issued.access, issued.csrf)
    assert current is not None
    return _session_document(current)


@router.post("/logout")
def logout(request: Request, response: Response, services: Services) -> dict[str, bool]:
    identity = _identity(services)
    _origin(request, services)
    try:
        identity.logout(
            request.cookies.get(f"{services.cookie_prefix}refresh", ""),
            request.cookies.get(f"{services.cookie_prefix}csrf", ""),
            request.headers.get("X-CSRF-Token", ""),
        )
    except AuthenticationDenied:
        raise HTTPException(401, "invalid credentials") from None
    _clear(response, services)
    return {"logged_out": True}
