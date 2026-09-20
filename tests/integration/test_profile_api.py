import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import partial
from threading import Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.adapters.database.profiles import PostgresCustomerProfileRepository
from backend.adapters.database.uow import PostgresUnitOfWork, create_unit_of_work
from backend.app.feedback.entities import AnalystVerdict
from backend.app.profile.entities import Customer, ProfileObservation
from backend.app.profile.gate import ProfileUpdateAction, ProfileUpdateGate
from backend.config import Settings
from backend.main import create_app

pytestmark = pytest.mark.postgres


@pytest.fixture
def profile_api(db_engine, profile, transaction):
    anchor = (datetime.now(UTC) - timedelta(days=1)).replace(
        hour=7, minute=0, second=0, microsecond=0
    )
    delta = anchor - profile.as_of
    profile = replace(
        profile,
        customer_id=uuid4(),
        as_of=anchor,
        observations=tuple(replace(o, timestamp=o.timestamp + delta) for o in profile.observations),
    )
    transaction = replace(transaction, customer_id=profile.customer_id, timestamp=anchor)
    with PostgresUnitOfWork(db_engine) as uow:
        uow.customers.add(Customer(profile.customer_id, anchor - timedelta(days=300)))
        for observation in profile.observations:
            uow.transactions.add(
                replace(
                    transaction,
                    transaction_id=observation.transaction_id,
                    amount=observation.amount,
                    timestamp=observation.timestamp,
                    recipient_id=observation.recipient_id,
                )
            )
        uow.profiles.save(profile, expected_version=0)
        uow.commit()
    tokens = {"admin": "a" * 43, "analyst": "b" * 43, "service": "c" * 43, "outsider": "d" * 43}
    entries = [
        {
            "principal_id": str(uuid4()),
            "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "roles": [role if role != "outsider" else "analyst"],
            "customer_ids": [str(profile.customer_id)] if role != "outsider" else [],
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
        for role, token in tokens.items()
    ]
    settings = Settings(
        environment="test", database_url=None, api_principals=json.dumps(entries), _env_file=None
    )
    app = create_app(settings, uow_factory=partial(create_unit_of_work, db_engine))
    with TestClient(app) as client:
        yield client, profile, transaction, tokens


def request(client, profile, tokens, *, currency="KZT", role="analyst", **params):
    return client.get(
        f"/api/v1/customers/{profile.customer_id}/profiles/{currency}",
        params=params,
        headers={"Authorization": "Bearer " + tokens[role]},
    )


def test_profile_api_statistics_scope_and_decimal_contract(profile_api):
    client, profile, _, tokens = profile_api
    for role in ("admin", "service", "analyst"):
        response = request(
            client, profile, tokens, role=role, as_of=profile.as_of.isoformat(), version=1
        )
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        body = response.json()
        assert body["status"] == "SUFFICIENT_HISTORY" and body["version"] == 1
        assert body["long_term"]["amounts"] == {
            "count": 20,
            "median": "30000.00",
            "mad": "5000.00",
            "p95": "50000.00",
            "mean": "32000.00",
        }
        assert body["short_term"]["typical_local_hours"] == [12]
        assert body["short_term"]["local_hour_counts"][12] == 20
        assert body["admission_workflow_verified"] is False
        assert "risk_score" not in body
    path = f"/api/v1/customers/{profile.customer_id}/profiles/KZT"
    assert client.get(path).status_code == 401
    denied = request(client, profile, tokens, role="outsider")
    missing = request(client, replace(profile, customer_id=uuid4()), tokens, role="admin")
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json() == {"detail": "customer not found"}


def test_missing_currency_profile_does_not_mix_or_create_history(profile_api, db_engine):
    client, profile, _, tokens = profile_api
    response = request(client, profile, tokens, currency="USD")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "UNINITIALIZED" and body["version"] is None
    assert body["long_term"]["amounts"] is None and body["short_term"]["count"] == 0
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.profiles.get(profile.customer_id, "USD") is None
        assert uow.profiles.get(profile.customer_id, "KZT").version == 1


@pytest.mark.parametrize(
    "params,status",
    [
        ({"version": 0}, 422),
        ({"version": 999}, 404),
        ({"as_of": "2020-01-01T00:00:00Z"}, 422),
        ({"as_of": "2020-01-01T00:00:00Z", "version": 1}, 409),
        ({"as_of": "2020-01-01T00:00:00", "version": 1}, 422),
        ({"as_of": "2999-01-01T00:00:00Z", "version": 1}, 422),
    ],
)
def test_invalid_or_unavailable_profile_queries(profile_api, params, status):
    client, profile, _, tokens = profile_api
    assert request(client, profile, tokens, **params).status_code == status
    assert request(client, profile, tokens, currency="kzt").status_code == 422


def test_old_revision_excludes_later_admission_and_retains_its_policy(profile_api, db_engine):
    client, original, transaction, tokens = profile_api
    late = replace(
        transaction,
        transaction_id=uuid4(),
        amount=Decimal("8000000"),
        timestamp=original.as_of - timedelta(days=5),
    )
    observation = ProfileObservation(
        late.transaction_id, late.amount, late.timestamp, late.recipient_id
    )
    updated = replace(
        original,
        version=2,
        observations=(*original.observations, observation),
        timezone="UTC",
        long_window_days=365,
        short_window_days=10,
    )
    with PostgresUnitOfWork(db_engine) as uow:
        uow.transactions.add(late)
        uow.profiles.save(updated, expected_version=1)
        uow.commit()
    # Same event cutoff, different knowledge version. A backdated admission must not
    # appear in the historical version or change its timezone/window definitions.
    first = request(client, original, tokens, as_of=original.as_of.isoformat(), version=1).json()
    second = request(client, original, tokens, as_of=original.as_of.isoformat(), version=2).json()
    assert first["long_term"]["count"] == 20 and second["long_term"]["count"] == 21
    assert first["timezone"] == "Asia/Almaty" and second["timezone"] == "UTC"
    assert first["short_term"]["days"] == 30 and second["short_term"]["days"] == 10


def test_expired_head_still_has_replayable_prior_revision(profile_api, db_engine):
    client, profile, _, tokens = profile_api
    with PostgresUnitOfWork(db_engine) as uow:
        uow.profiles.save(
            replace(profile, as_of=profile.as_of + timedelta(days=200), observations=(), version=2),
            expected_version=1,
        )
        uow.commit()
    # The latest head is ahead of now; fail explicitly, not an invented empty current baseline.
    assert request(client, profile, tokens).status_code == 409
    replay = request(client, profile, tokens, version=1, as_of=profile.as_of.isoformat())
    assert replay.status_code == 200 and replay.json()["long_term"]["count"] == 20


def test_strict_cutoffs_and_independent_currency_windows(profile_api, db_engine):
    client, profile, transaction, tokens = profile_api
    offsets = [180, 30, 1, 0]
    usd_observations = []
    with PostgresUnitOfWork(db_engine) as uow:
        for days in offsets:
            tx = replace(
                transaction,
                transaction_id=uuid4(),
                currency="USD",
                amount=Decimal("10"),
                timestamp=profile.as_of - timedelta(days=days),
            )
            uow.transactions.add(tx)
            usd_observations.append(
                ProfileObservation(tx.transaction_id, tx.amount, tx.timestamp, tx.recipient_id)
            )
        usd = replace(profile, currency="USD", observations=tuple(usd_observations))
        uow.profiles.save(usd, expected_version=0)
        uow.commit()
    result = request(
        client, profile, tokens, currency="USD", version=1, as_of=profile.as_of.isoformat()
    ).json()
    assert result["long_term"]["count"] == 2  # 180d boundary and candidate instant excluded.
    assert result["short_term"]["count"] == 1  # 30d boundary also excluded.
    assert result["long_term"]["amounts"]["median"] == "10.00"
    assert result["status"] == "INSUFFICIENT_HISTORY"


def test_exceptional_confirmed_purchase_and_raw_intake_do_not_poison_baseline(
    profile_api, db_engine
):
    client, profile, transaction, tokens = profile_api
    car = replace(transaction, amount=Decimal("8000000"))
    decision, unchanged = ProfileUpdateGate().apply(car, profile, AnalystVerdict.LEGITIMATE)
    assert decision.action == ProfileUpdateAction.QUARANTINE and unchanged is profile
    with PostgresUnitOfWork(db_engine) as uow:
        uow.transactions.add(car)
        uow.commit()
    result = request(client, profile, tokens).json()
    assert result["version"] == 1 and result["long_term"]["count"] == 20
    assert result["long_term"]["amounts"]["median"] == "30000.00"
    future_fraud = replace(car, transaction_id=uuid4(), amount=Decimal("500000"))
    assert (
        ProfileUpdateGate().apply(future_fraud, profile, AnalystVerdict.CONFIRMED_FRAUD)[1]
        is profile
    )


@pytest.mark.parametrize(
    "operation",
    [
        "UPDATE profile_revisions SET timezone='UTC' WHERE customer_id=:id",
        "DELETE FROM profile_revisions WHERE customer_id=:id",
        "TRUNCATE profile_revisions",
    ],
)
def test_revision_history_is_immutable(profile_api, db_engine, operation):
    _, profile, _, _ = profile_api
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(text(operation), {"id": profile.customer_id})


def test_later_transaction_cannot_append_to_committed_revision(profile_api, db_engine):
    _, profile, transaction, _ = profile_api
    with PostgresUnitOfWork(db_engine) as uow:
        uow.transactions.add(transaction)
        uow.commit()
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO profile_observations
            (transaction_id, customer_id, currency, admitted_version, ordinal)
            VALUES (:tx, :customer, 'KZT', 1, 20)"""),
            {"tx": transaction.transaction_id, "customer": profile.customer_id},
        )
    with PostgresUnitOfWork(db_engine) as uow:
        assert (
            len(uow.profiles.get_revision(profile.customer_id, "KZT", version=1).observations) == 20
        )


def test_revision_rolls_back_with_failed_unit_of_work(profile_api, db_engine):
    _, profile, transaction, _ = profile_api
    _, updated = ProfileUpdateGate().apply(transaction, profile, AnalystVerdict.LEGITIMATE)
    with PostgresUnitOfWork(db_engine) as uow:
        uow.transactions.add(transaction)
        uow.profiles.save(updated, expected_version=1)
        # No commit: transaction, admission, head and revision all roll back.
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.profiles.get_revision(profile.customer_id, "KZT", version=2) is None
        assert uow.profiles.get(profile.customer_id, "KZT").version == 1
        assert uow.transactions.get(transaction.transaction_id) is None


def test_reader_pins_revision_before_concurrent_writer(profile_api, db_engine, monkeypatch):
    client, profile, transaction, tokens = profile_api
    captured, committed = Event(), Event()
    hydrate = PostgresCustomerProfileRepository._hydrate

    def delayed_hydrate(self, row):
        captured.set()
        assert committed.wait(5)
        return hydrate(self, row)

    monkeypatch.setattr(PostgresCustomerProfileRepository, "_hydrate", delayed_hydrate)

    def writer():
        assert captured.wait(5)
        _, updated = ProfileUpdateGate().apply(transaction, profile, AnalystVerdict.LEGITIMATE)
        with PostgresUnitOfWork(db_engine) as uow:
            uow.transactions.add(transaction)
            uow.profiles.save(updated, expected_version=1)
            uow.commit()
        committed.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        write = pool.submit(writer)
        read = pool.submit(request, client, profile, tokens)
        response = read.result(timeout=10)
        write.result(timeout=10)
    assert response.status_code == 200
    assert response.json()["version"] == 1 and response.json()["long_term"]["count"] == 20
    assert request(client, profile, tokens).json()["version"] == 2
