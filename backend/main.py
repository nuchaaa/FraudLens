import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from urllib.parse import urlsplit

from fastapi import FastAPI
from sqlalchemy.engine import Engine
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.adapters.database.base import create_database_engine
from backend.adapters.database.grants import verify_runtime_role
from backend.adapters.database.uow import create_unit_of_work
from backend.adapters.evaluation import ExperimentalEvaluationEngine
from backend.adapters.passwords import Argon2Passwords
from backend.adapters.security import CredentialRegistry
from backend.adapters.webauthn import PyWebAuthnVerifier
from backend.api import auth, console, evaluations, health, learning, profiles, transactions
from backend.api.dependencies import ApiServices
from backend.api.errors import install_error_handlers
from backend.api.limits import BusinessRequestLimits
from backend.app.identity.service import IdentityService
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
    trusted_host: str | None = None
    if config.human_auth_enabled:
        # Local WebAuthn is incomplete: factor lifecycle and verified recovery
        # remain absent. Do not expose human sessions through production mode.
        if config.environment == "production":
            raise ValueError("production human authentication requires verified MFA and recovery")
        origin = urlsplit(config.human_origin or "")
        if (
            origin.scheme not in ("http", "https")
            or not origin.hostname
            or origin.username
            or origin.password
            or origin.path
            or origin.query
            or origin.fragment
            or config.human_origin != f"{origin.scheme}://{origin.netloc}"
            or (origin.scheme == "http" and origin.hostname not in ("127.0.0.1", "localhost"))
        ):
            raise ValueError("human authentication requires an explicit trusted origin")
        trusted_host = origin.hostname

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
        try:
            if config.environment == "production" and uow_factory is None:
                if engine is None:
                    raise ValueError("production API requires its own PostgreSQL runtime login")
                with engine.connect() as connection:
                    verify_runtime_role(connection, "api")
            identity = (
                IdentityService(
                    factory,
                    Argon2Passwords(),
                    service_principal_ids=credentials.principal_ids,
                    webauthn=PyWebAuthnVerifier(),
                    origin=config.human_origin,
                )
                if config.human_auth_enabled and factory is not None
                else None
            )
            if identity is not None:
                identity.ensure_no_collisions()
            app.state.services = ApiServices(
                credentials,
                factory,
                config.experimental_enabled,
                evaluation_engine,
                identity,
                config.human_origin,
                not config.human_local_insecure,
            )
            logging.getLogger("fraudlens").info("FraudLens transaction API started")
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
    if trusted_host is not None:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=[trusted_host])
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(transactions.router)
    app.include_router(console.router)
    app.include_router(profiles.router)
    app.include_router(evaluations.router)
    app.include_router(learning.router)
    return app


app = create_app()
