import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from backend.adapters.database.base import create_database_engine
from backend.adapters.database.uow import create_unit_of_work
from backend.adapters.evaluation import ExperimentalEvaluationEngine
from backend.adapters.security import CredentialRegistry
from backend.api import console, evaluations, health, learning, profiles, transactions
from backend.api.dependencies import ApiServices
from backend.api.errors import install_error_handlers
from backend.api.limits import BusinessRequestLimits
from backend.app.transaction.service import UnitOfWorkFactory
from backend.config import Settings
from backend.logging_config import configure_logging


def create_app(
    settings: Settings | None = None,
    *,
    uow_factory: UnitOfWorkFactory | None = None,
) -> FastAPI:
    config = settings or Settings()
    credentials = CredentialRegistry(
        config.api_principals.get_secret_value() if config.api_principals else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(config.log_level)
        evaluation_engine = ExperimentalEvaluationEngine(
            config.experimental_model_bundle if config.experimental_enabled else None,
            config.experimental_manifest_sha256 if config.experimental_enabled else None,
        )
        engine: Engine | None = None
        factory = uow_factory
        if factory is None and config.database_url is not None:
            engine = create_database_engine(config.database_url.get_secret_value())
            database = engine
            factory = partial(create_unit_of_work, database)
        app.state.services = ApiServices(
            credentials, factory, config.experimental_enabled, evaluation_engine
        )
        logging.getLogger("fraudlens").info("FraudLens transaction API started")
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    app = FastAPI(
        title="FraudLens",
        version="0.1.0",
        lifespan=lifespan,
        description=(
            "Authenticated synthetic intake. "
            "Opt-in experimental evaluation and review; production-ineligible."
        ),
        docs_url=None if config.environment == "production" else "/docs",
        redoc_url=None,
        openapi_url=None if config.environment == "production" else "/openapi.json",
    )
    app.add_middleware(BusinessRequestLimits)
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(transactions.router)
    app.include_router(console.router)
    app.include_router(profiles.router)
    app.include_router(evaluations.router)
    app.include_router(learning.router)
    return app


app = create_app()
