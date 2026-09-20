import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url

from backend.adapters.database.base import create_database_engine


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set; disposable PostgreSQL required")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Persistence tests require a disposable database named *_test")
    schema = "fraudlens_test_" + uuid4().hex
    admin = create_database_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"})
    scoped = scoped_url.render_as_string(hide_password=False)
    previous = os.environ.get("FRAUDLENS_DATABASE_URL")
    engine = create_database_engine(scoped)
    try:
        os.environ["FRAUDLENS_DATABASE_URL"] = scoped
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        command.upgrade(config, "head")
        if previous is None:
            del os.environ["FRAUDLENS_DATABASE_URL"]
        else:
            os.environ["FRAUDLENS_DATABASE_URL"] = previous
        yield engine
    finally:
        if previous is None:
            os.environ.pop("FRAUDLENS_DATABASE_URL", None)
        else:
            os.environ["FRAUDLENS_DATABASE_URL"] = previous
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
