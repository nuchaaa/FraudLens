from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

pytestmark = pytest.mark.postgres


def test_migration_upgrade_downgrade_and_metadata_match(db_engine: Engine, monkeypatch):
    # db_engine belongs to this session's randomly named disposable schema, never public.
    monkeypatch.setenv(
        "FRAUDLENS_DATABASE_URL", db_engine.url.render_as_string(hide_password=False)
    )
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.check(config)
    command.downgrade(config, "0001_foundation")
    assert inspect(db_engine).get_table_names() == ["alembic_version"]
    command.upgrade(config, "head")
    command.check(config)
    assert len(inspect(db_engine).get_table_names()) == 15
