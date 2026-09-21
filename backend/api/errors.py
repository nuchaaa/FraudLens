from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, TimeoutError

from backend.app.cases.entities import InvalidCaseTransition
from backend.app.evaluation.contracts import EvaluationUnavailable
from backend.app.features.context import FeatureInputError
from backend.app.profile.learning import LearningInputError
from backend.app.profile.read_model import ProfileHistoryUnavailable, ProfileQueryError
from backend.app.shared.errors import (
    ConcurrentUpdate,
    DuplicateCustomer,
    DuplicateTransaction,
    HistoryConflict,
    IdempotencyConflict,
    PersistenceConflict,
)
from backend.app.shared.security import Forbidden, NotFound


def install_error_handlers(app: FastAPI) -> None:
    async def business_error(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, EvaluationUnavailable):
            status, detail = 503, str(exc)
        elif isinstance(exc, (ConcurrentUpdate, HistoryConflict, InvalidCaseTransition)):
            status, detail = 409, str(exc)
        elif isinstance(exc, (ProfileQueryError, FeatureInputError, LearningInputError)):
            status, detail = 422, str(exc)
        elif isinstance(exc, ProfileHistoryUnavailable):
            status, detail = 409, str(exc)
        elif isinstance(exc, Forbidden):
            status, detail = 403, str(exc)
        elif isinstance(exc, NotFound):
            status, detail = 404, str(exc)
        elif isinstance(exc, (DuplicateTransaction, DuplicateCustomer)):
            status, detail = 409, str(exc)
        elif isinstance(exc, IdempotencyConflict):
            status, detail = 409, "Idempotency-Key already used for a different request"
        elif isinstance(exc, (OperationalError, TimeoutError)):
            status, detail = 503, "transaction storage is temporarily unavailable"
        else:
            status, detail = 500, "transaction could not be completed"
        return JSONResponse(
            {"detail": detail}, status_code=status, headers={"Cache-Control": "no-store"}
        )

    async def validation_error(request: Request, exc: Exception) -> JSONResponse:
        # Do not echo request bodies, bearer credentials or Pydantic context values.
        assert isinstance(exc, RequestValidationError)
        errors = [{"loc": error["loc"], "type": error["type"]} for error in exc.errors()]
        return JSONResponse({"detail": errors}, status_code=422)

    for error in (
        EvaluationUnavailable,
        FeatureInputError,
        ConcurrentUpdate,
        HistoryConflict,
        InvalidCaseTransition,
        ProfileQueryError,
        LearningInputError,
        ProfileHistoryUnavailable,
        Forbidden,
        NotFound,
        PersistenceConflict,
        IdempotencyConflict,
        OperationalError,
        TimeoutError,
    ):
        app.add_exception_handler(error, business_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(Exception, business_error)
