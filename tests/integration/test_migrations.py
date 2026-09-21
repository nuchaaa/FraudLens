from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

from backend.adapters.database.uow import PostgresUnitOfWork
from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation

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
    assert len(inspect(db_engine).get_table_names()) == 22


def test_profile_revision_migration_preserves_existing_head_without_inventing_history(
    db_engine,
    monkeypatch,
    transaction,
):
    monkeypatch.setenv(
        "FRAUDLENS_DATABASE_URL", db_engine.url.render_as_string(hide_password=False)
    )
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.downgrade(config, "0003_history_guards")
    tx = replace(transaction, customer_id=uuid4())
    observation = ProfileObservation(tx.transaction_id, tx.amount, tx.timestamp, tx.recipient_id)
    original = CustomerBehaviorProfile(tx.customer_id, "KZT", tx.timestamp, (observation,))
    with db_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO customers VALUES (:customer,:created,'Asia/Almaty')"),
            {"customer": tx.customer_id, "created": tx.timestamp},
        )
        connection.execute(
            text("""INSERT INTO transactions VALUES
            (:transaction,:customer,:recipient,:amount,:currency,:timestamp,:channel,:device,:status)"""),
            {
                "transaction": tx.transaction_id,
                "customer": tx.customer_id,
                "recipient": tx.recipient_id,
                "amount": tx.amount,
                "currency": tx.currency,
                "timestamp": tx.timestamp,
                "channel": tx.channel.value,
                "device": tx.device_id,
                "status": tx.status.value,
            },
        )
        connection.execute(
            text("""INSERT INTO profiles VALUES
            (:customer,'KZT',1,:as_of,'Asia/Almaty',180,30)"""),
            {"customer": tx.customer_id, "as_of": tx.timestamp},
        )
        connection.execute(
            text("INSERT INTO profile_observations VALUES (:transaction,:customer,'KZT',1,0)"),
            {"transaction": tx.transaction_id, "customer": tx.customer_id},
        )
    updated = replace(original, version=2, as_of=original.as_of + timedelta(days=1), timezone="UTC")
    with db_engine.begin() as connection:
        connection.execute(
            text("""UPDATE profiles SET version=2,as_of=:as_of,timezone='UTC'
            WHERE customer_id=:customer AND currency='KZT'"""),
            {"customer": tx.customer_id, "as_of": updated.as_of},
        )
    command.upgrade(config, "head")
    command.check(config)
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.profiles.get_revision(tx.customer_id, "KZT", version=1) is None
        assert uow.profiles.get_revision(tx.customer_id, "KZT", version=2) == updated
        assert uow.transactions.get(tx.transaction_id) == tx
