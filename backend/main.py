import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.health import router
from backend.config import Settings
from backend.logging_config import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(config.log_level)
        logging.getLogger("fraudlens").info("FraudLens foundation started")
        yield

    app = FastAPI(
        title="FraudLens",
        version="0.1.0",
        lifespan=lifespan,
        description="Persistence foundation. Transaction evaluation is not implemented yet.",
        docs_url=None if config.environment == "production" else "/docs",
        redoc_url=None,
        openapi_url=None if config.environment == "production" else "/openapi.json",
    )
    app.include_router(router)
    return app


app = create_app()
