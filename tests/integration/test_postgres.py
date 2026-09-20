import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url

from backend.adapters.database.base import create_database_engine


@pytest.mark.postgres
def test_postgres_connection_and_migration(monkeypatch: pytest.MonkeyPatch) -> None:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set; disposable PostgreSQL required")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Migration smoke tests require a disposable database named *_test")
    monkeypatch.setenv("FRAUDLENS_DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_database_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == ScriptDirectory.from_config(config).get_current_head()
            )
    finally:
        engine.dispose()


def test_sqlite_is_not_silently_substituted() -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        create_database_engine("sqlite://")
