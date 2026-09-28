"""Authenticated read-only access to clearly fictional local demo evidence."""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from backend.adapters.demo.simulator import export_documents
from backend.api.dependencies import ApiServices, authenticated_principal, get_services
from backend.app.demo.evidence import build_evidence_package
from backend.app.demo.scenarios import build_plan
from backend.app.demo.simulator import build_simulation
from backend.app.shared.security import Principal, Role

router = APIRouter(prefix="/api/v1/experimental/demo", tags=["synthetic demo evidence"])
type Auth = Annotated[Principal, Depends(authenticated_principal)]
type Services = Annotated[ApiServices, Depends(get_services)]


@lru_cache(maxsize=1)
def _controlled_report() -> str:
    """Stable in-memory report; no analyst or PostgreSQL state is consulted."""
    return export_documents(build_simulation())["scenario_manifest.json"]


@router.get("/controlled-scenarios")
def get_controlled_scenarios(principal: Auth, services: Services) -> Response:
    if not services.experimental_enabled:
        raise HTTPException(503, "experimental demo is disabled")
    if Role.ADMIN not in principal.roles:
        raise HTTPException(403, "controlled simulator requires admin role")
    return Response(
        _controlled_report(), media_type="application/json", headers={"Cache-Control": "no-store"}
    )


@router.get("/evidence/{transaction_id}")
def get_demo_evidence(
    transaction_id: UUID,
    principal: Auth,
    services: Services,
    response: Response,
) -> dict[str, object]:
    if not services.experimental_enabled:
        raise HTTPException(503, "experimental demo evidence is disabled")
    entry = build_evidence_package(build_plan()).find(transaction_id)
    if entry is None or not principal.can_read(entry.customer_id):
        raise HTTPException(404, "demo evidence not found")
    response.headers["Cache-Control"] = "no-store"
    return entry.document()
