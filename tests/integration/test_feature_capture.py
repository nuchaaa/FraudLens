import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import partial
from uuid import uuid4

import pytest

from backend.adapters.database.uow import PostgresUnitOfWork, create_unit_of_work
from backend.adapters.features.__main__ import main
from backend.adapters.features.artifacts import decode_context, encode_context
from backend.app.features.context import ActivityHistoryLimit, FeatureInputError
from backend.app.features.engine import extract_features
from backend.app.features.service import FeatureService
from backend.app.profile.entities import Customer, CustomerBehaviorProfile, ProfileObservation
from backend.app.shared.security import NotFound, Principal, Role

pytestmark = pytest.mark.postgres


@pytest.fixture
def feature_store(db_engine, transaction):
    now = datetime.now(UTC)
    tx = replace(transaction, customer_id=uuid4(), timestamp=now - timedelta(hours=1))
    principal = Principal(uuid4(), frozenset({Role.SERVICE}), frozenset({tx.customer_id}))
    with PostgresUnitOfWork(db_engine) as uow:
        uow.customers.add(Customer(tx.customer_id, now - timedelta(days=365)))
        uow.transactions.add(tx)
        uow.commit()
    return tx, principal, FeatureService(partial(create_unit_of_work, db_engine))


def test_database_history_scopes_boundaries_and_candidate_exclusion(feature_store, db_engine):
    tx, principal, service = feature_store
    other_customer = uuid4()
    offsets = [
        timedelta(days=181),
        timedelta(days=180),
        timedelta(days=180, microseconds=-1),
        timedelta(minutes=60),
        timedelta(minutes=10),
        timedelta(minutes=5),
        timedelta(minutes=1),
        timedelta(0),
        timedelta(minutes=-1),
    ]
    with PostgresUnitOfWork(db_engine) as uow:
        uow.customers.add(Customer(other_customer, tx.timestamp))
        for offset in offsets:
            uow.transactions.add(
                replace(tx, transaction_id=uuid4(), timestamp=tx.timestamp - offset)
            )
        for field, value in (("currency", "USD"), ("customer_id", other_customer)):
            uow.transactions.add(
                replace(
                    tx,
                    transaction_id=uuid4(),
                    timestamp=tx.timestamp - timedelta(minutes=1),
                    **{field: value},
                )
            )
        uow.commit()
    context = service.capture(principal, tx.transaction_id, profile_version=None)
    assert len(context.activity) == 5
    assert all(
        item.customer_id == tx.customer_id and item.currency == "KZT" for item in context.activity
    )
    assert all(
        item.transaction_id != tx.transaction_id and item.timestamp < tx.timestamp
        for item in context.activity
    )
    values = dict(
        zip(extract_features(context).names, extract_features(context).values, strict=True)
    )
    assert values["transactions_last_5_min"] == 1
    assert values["transactions_last_10_min"] == 2
    assert values["transactions_last_hour"] == 3
    assert context.profile is None and values["baseline_insufficient"] == 1


def test_late_arrivals_do_not_change_saved_context_replay(feature_store, db_engine):
    tx, principal, service = feature_store
    initial = service.capture(principal, tx.transaction_id, profile_version=None)
    artifact = encode_context(initial)
    expected = extract_features(initial)
    with PostgresUnitOfWork(db_engine) as uow:
        uow.transactions.add(
            replace(
                tx,
                transaction_id=uuid4(),
                amount=Decimal("8000000"),
                timestamp=tx.timestamp - timedelta(minutes=1),
            )
        )
        uow.commit()
    assert extract_features(decode_context(artifact)) == expected
    fresh = service.capture(principal, tx.transaction_id, profile_version=None)
    assert extract_features(fresh) != expected
    assert fresh.profile is None  # Raw intake never becomes admitted history.
    assert len(initial.activity) == 0 and len(fresh.activity) == 1


def test_explicit_profile_revision_and_later_admission_isolation(feature_store, db_engine):
    tx, principal, service = feature_store
    history = tuple(
        replace(tx, transaction_id=uuid4(), timestamp=tx.timestamp - timedelta(days=i + 1))
        for i in range(5)
    )
    observations = tuple(
        ProfileObservation(t.transaction_id, t.amount, t.timestamp, t.recipient_id) for t in history
    )
    profile = CustomerBehaviorProfile(tx.customer_id, "KZT", tx.timestamp, observations)
    with PostgresUnitOfWork(db_engine) as uow:
        for item in history:
            uow.transactions.add(item)
        uow.profiles.save(profile, expected_version=0)
        uow.commit()
    with pytest.raises(FeatureInputError, match="explicit"):
        service.capture(principal, tx.transaction_id, profile_version=None)
    initial = service.capture(principal, tx.transaction_id, profile_version=1)
    artifact = encode_context(initial)
    late = replace(
        tx,
        transaction_id=uuid4(),
        timestamp=tx.timestamp - timedelta(days=2),
        amount=Decimal("8000000"),
    )
    with PostgresUnitOfWork(db_engine) as uow:
        uow.transactions.add(late)
        uow.profiles.save(
            replace(
                profile,
                version=2,
                observations=(
                    *observations,
                    ProfileObservation(
                        late.transaction_id, late.amount, late.timestamp, late.recipient_id
                    ),
                ),
            ),
            expected_version=1,
        )
        uow.commit()
    assert extract_features(decode_context(artifact)) == extract_features(initial)
    pinned = service.capture(principal, tx.transaction_id, profile_version=1)
    assert len(pinned.profile.observations) == 5
    assert (
        len(service.capture(principal, tx.transaction_id, profile_version=2).profile.observations)
        == 6
    )
    with pytest.raises(NotFound, match="revision"):
        service.capture(principal, tx.transaction_id, profile_version=999)


def test_capture_scope_missing_transaction_and_invalid_revision(feature_store):
    tx, principal, service = feature_store
    with pytest.raises(NotFound, match="transaction not found"):
        service.capture(
            Principal(uuid4(), frozenset({Role.ANALYST})), tx.transaction_id, profile_version=None
        )
    with pytest.raises(NotFound, match="transaction not found"):
        service.capture(principal, uuid4(), profile_version=None)
    with pytest.raises(FeatureInputError):
        service.capture(principal, tx.transaction_id, profile_version=0)


def test_history_limit_fails_instead_of_silently_truncating(feature_store, db_engine):
    tx, _, _ = feature_store
    with PostgresUnitOfWork(db_engine) as uow:
        for i in range(3):
            uow.transactions.add(
                replace(
                    tx, transaction_id=uuid4(), timestamp=tx.timestamp - timedelta(minutes=i + 1)
                )
            )
        uow.commit()
    with pytest.raises(ActivityHistoryLimit), PostgresUnitOfWork(db_engine) as uow:
        uow.transactions.history_before(
            tx.customer_id,
            "KZT",
            since=tx.timestamp - timedelta(days=1),
            before=tx.timestamp,
            exclude_transaction_id=tx.transaction_id,
            limit=2,
        )


def test_history_tie_order_is_stable_and_capture_is_read_only(feature_store, db_engine):
    tx, principal, service = feature_store
    same_time = tx.timestamp - timedelta(minutes=1)
    history = tuple(
        replace(tx, transaction_id=uuid4(), timestamp=same_time, device_id=device)
        for device in ("first-device", "second-device")
    )
    with PostgresUnitOfWork(db_engine) as uow:
        for item in reversed(history):
            uow.transactions.add(item)
        uow.commit()
    captured = service.capture(principal, tx.transaction_id, profile_version=None)
    assert [item.transaction_id for item in captured.activity] == sorted(
        (t.transaction_id for t in history), key=str
    )
    values = dict(
        zip(extract_features(captured).names, extract_features(captured).values, strict=True)
    )
    assert values["device_change_missing"] == 1
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.profiles.get(tx.customer_id, "KZT") is None
        assert uow.transactions.get(tx.transaction_id) == tx


def test_authenticated_cli_capture_and_database_free_replay(
    feature_store,
    db_engine,
    monkeypatch,
    tmp_path,
    capsys,
):
    tx, principal, _ = feature_store
    token = "z" * 43  # Synthetic test credential only.
    registry = [
        {
            "principal_id": str(principal.principal_id),
            "roles": ["service"],
            "customer_ids": [str(tx.customer_id)],
            "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
    ]
    monkeypatch.setenv(
        "FRAUDLENS_DATABASE_URL", db_engine.url.render_as_string(hide_password=False)
    )
    monkeypatch.setenv("FRAUDLENS_API_PRINCIPALS", json.dumps(registry))
    monkeypatch.setenv("FRAUDLENS_FEATURE_TOKEN", token)
    path = tmp_path / "context.json"
    args = [
        "capture",
        "--transaction-id",
        str(tx.transaction_id),
        "--without-profile",
        "--output",
        str(path),
    ]
    assert main(args) == 0
    original = capsys.readouterr()
    output = json.loads(original.out)
    assert output["feature_version"] == "behavior-v1" and len(output["features"]) == 29
    assert token not in path.read_text() and token not in original.out
    artifact = path.read_text()
    assert main(args) == 1  # Export refuses to replace a previously captured artifact.
    assert path.read_text() == artifact
    capsys.readouterr()
    monkeypatch.setenv("FRAUDLENS_FEATURE_TOKEN", "bad")
    assert main([*args[:-1], str(tmp_path / "denied.json")]) == 1
    assert "valid bearer" in capsys.readouterr().err
    assert not (tmp_path / "denied.json").exists()
    with PostgresUnitOfWork(db_engine) as uow:
        uow.transactions.add(
            replace(tx, transaction_id=uuid4(), timestamp=tx.timestamp - timedelta(minutes=1))
        )
        uow.commit()
    monkeypatch.setenv("FRAUDLENS_DATABASE_URL", "not-a-database-url")
    monkeypatch.setenv("FRAUDLENS_API_PRINCIPALS", "invalid registry")
    assert main(["replay", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == output
