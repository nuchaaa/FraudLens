from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    stage: str


@router.get("/health/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    """Process liveness only; does not imply database or model readiness."""
    return HealthResponse(status="ok", version="0.1.0", stage="persistence-foundation")
