import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import partial
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.adapters.database.history import PostgresAuditRepository
from backend.adapters.database.uow import PostgresUnitOfWork, create_unit_of_work
from backend.app.profile.entities import Customer
from backend.config import Settings
from backend.main import create_app

pytestmark = pytest.mark.postgres
BASE = "/api/v1/experimental"
TOKENS = {
    "admin": "a" * 43,
    "analyst1": "b" * 43,
    "analyst2": "c" * 43,
    "service": "d" * 43,
}


def headers(role: str, key: str | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {TOKENS[role]}"}
    if key is not None:
        result["Idempotency-Key"] = key
    return result


@pytest.fixture
def learning_api(db_engine, transaction):
    customer_id = uuid4()
    start = datetime.now(UTC) - timedelta(days=20)
    transactions = tuple(
        replace(
            transaction,
            transaction_id=uuid4(),
            customer_id=customer_id,
            amount=Decimal("8000000") if index == 6 else Decimal(20_000 + index * 1_000),
            timestamp=start + timedelta(days=index),
        )
        for index in range(12)
    )
    entries = [
        {
            "principal_id": str(uuid4()),
            "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "roles": ["analyst" if role.startswith("analyst") else role],
            "customer_ids": [str(customer_id)],
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
        for role, token in TOKENS.items()
    ]
    with PostgresUnitOfWork(db_engine) as uow:
        uow.customers.add(Customer(customer_id, start - timedelta(days=1), "UTC"))
        for item in transactions:
            uow.transactions.add(item)
        uow.commit()
    settings = Settings(
        environment="test",
        api_principals=json.dumps(entries),
        experimental_enabled=True,
        _env_file=None,
    )
    with TestClient(
        create_app(settings, uow_factory=partial(create_unit_of_work, db_engine)),
        raise_server_exceptions=False,
    ) as client:
        yield client, transactions, entries


def reviewed_case(
    client,
    transaction_id,
    index,
    reviewer="analyst1",
    verdict="LEGITIMATE",
    profile_version=None,
):
    evaluated = client.post(
        BASE + "/evaluations",
        json={
            "transaction_id": str(transaction_id),
            "profile_version": profile_version,
            "strategy": "rules_only",
        },
        headers=headers("service", f"evaluation-{index}"),
    )
    assert evaluated.status_code == 201, evaluated.text
    opened = client.post(
        BASE + "/cases",
        json={"evaluation_id": evaluated.json()["evaluation_id"]},
        headers=headers(reviewer, f"case-{index}"),
    )
    assert opened.status_code == 201, opened.text
    case_id = opened.json()["case_id"]
    started = client.post(
        BASE + f"/cases/{case_id}/review",
        json={"expected_version": 0, "action": "start_review"},
        headers=headers(reviewer, f"start-{index}"),
    )
    assert started.status_code == 200, started.text
    terminal = client.post(
        BASE + f"/cases/{case_id}/review",
        json={
            "expected_version": 1,
            "action": "feedback",
            "verdict": verdict,
            "comment": "Independent synthetic review evidence",
        },
        headers=headers(reviewer, f"verdict-{index}"),
    )
    assert terminal.status_code == 200, terminal.text
    closed = client.post(
        BASE + f"/cases/{case_id}/review",
        json={"expected_version": 3, "action": "close"},
        headers=headers(reviewer, f"close-{index}"),
    )
    assert closed.status_code == 200, closed.text
    return case_id


def bootstrap(client, case_ids, key="bootstrap"):
    return client.post(
        BASE + "/profile-learning/bootstrap",
        json={"case_ids": case_ids},
        headers=headers("admin", key),
    )


def test_reviewed_bootstrap_exact_replay_and_verified_profile(learning_api, db_engine):
    client, transactions, entries = learning_api
    case_ids = [
        reviewed_case(client, item.transaction_id, index, f"analyst{index % 2 + 1}")
        for index, item in enumerate(transactions[:5])
    ]
    result = bootstrap(client, case_ids)
    assert result.status_code == 201, result.text
    doc = result.json()
    assert doc["action"] == "ACCEPT" and doc["profile_version_after"] == 1
    assert doc["admission_workflow_verified"] is True
    assert doc["low_weight_applied"] is doc["correction_applied"] is False
    assert doc["actor_id"] == entries[0]["principal_id"]
    replay = bootstrap(client, list(reversed(case_ids)))
    assert replay.content == result.content
    assert replay.headers["idempotency-replayed"] == "true"
    fetched = client.get(result.headers["location"], headers=headers("admin"))
    assert fetched.content == result.content
    profile = client.get(
        f"/api/v1/customers/{transactions[0].customer_id}/profiles/KZT",
        headers=headers("analyst1"),
    ).json()
    assert profile["version"] == 1 and profile["long_term"]["count"] == 5
    assert profile["admission_workflow_verified"] is True
    assert profile["admission_policy_version"] == "profile-learning-v1-experimental"
    assert profile["learning_decision_id"] == doc["decision_id"]
    with PostgresUnitOfWork(db_engine) as uow:
        stored = uow.profiles.get(transactions[0].customer_id, "KZT")
        assert stored is not None and stored.version == 1
        assert stored.admission_workflow_verified


def test_ordinary_accept_exception_quarantine_and_fraud_reject(learning_api, db_engine):
    client, transactions, _ = learning_api
    bootstrap_cases = [
        reviewed_case(client, item.transaction_id, index, f"analyst{index % 2 + 1}")
        for index, item in enumerate(transactions[:5])
    ]
    assert bootstrap(client, bootstrap_cases).status_code == 201
    ordinary_case = reviewed_case(
        client, transactions[5].transaction_id, 5, "analyst1", profile_version=1
    )
    accepted = client.post(
        BASE + "/profile-learning/case",
        json={"case_id": ordinary_case, "expected_profile_version": 1},
        headers=headers("admin", "ordinary-update"),
    )
    assert accepted.status_code == 201 and accepted.json()["action"] == "ACCEPT"
    exceptional = transactions[6]
    exceptional_case = reviewed_case(
        client, exceptional.transaction_id, 6, "analyst2", profile_version=2
    )
    quarantined = client.post(
        BASE + "/profile-learning/case",
        json={"case_id": exceptional_case, "expected_profile_version": 2},
        headers=headers("admin", "exceptional-update"),
    )
    assert quarantined.status_code == 201
    assert quarantined.json()["action"] == "QUARANTINE"
    assert quarantined.json()["reason"] == "EXCEPTIONAL_LEGITIMATE_AMOUNT"
    fraud_case = reviewed_case(
        client,
        transactions[7].transaction_id,
        7,
        "analyst1",
        "CONFIRMED_FRAUD",
        profile_version=2,
    )
    rejected = client.post(
        BASE + "/profile-learning/case",
        json={"case_id": fraud_case, "expected_profile_version": 2},
        headers=headers("admin", "fraud-update"),
    )
    assert rejected.status_code == 201
    assert rejected.json()["action"] == "REJECT_FROM_PROFILE"
    with PostgresUnitOfWork(db_engine) as uow:
        profile = uow.profiles.get(transactions[0].customer_id, "KZT")
        assert profile is not None and profile.version == 2
        assert exceptional.transaction_id not in {o.transaction_id for o in profile.observations}
        assert transactions[7].transaction_id not in {
            o.transaction_id for o in profile.observations
        }


def test_cold_case_quarantined_and_single_verdict_cannot_self_authorize(learning_api):
    client, transactions, _ = learning_api
    case_id = reviewed_case(client, transactions[0].transaction_id, 0, "analyst1")
    cold = client.post(
        BASE + "/profile-learning/case",
        json={"case_id": case_id, "expected_profile_version": None},
        headers=headers("admin", "cold"),
    )
    assert cold.status_code == 201
    assert cold.json()["reason"] == "COLD_START_REQUIRES_BOOTSTRAP"
    assert cold.json()["profile_version_after"] is None
    assert bootstrap(client, [case_id] * 5, "duplicates").status_code == 422


def test_stale_absent_profile_evaluation_cannot_update_bootstrapped_profile(learning_api):
    client, transactions, _ = learning_api
    stale_case = reviewed_case(client, transactions[5].transaction_id, 20, "analyst1")
    cases = [
        reviewed_case(client, item.transaction_id, index, f"analyst{index % 2 + 1}")
        for index, item in enumerate(transactions[:5])
    ]
    assert bootstrap(client, cases).status_code == 201
    result = client.post(
        BASE + "/profile-learning/case",
        json={"case_id": stale_case, "expected_profile_version": 1},
        headers=headers("admin", "stale-capture"),
    )
    assert result.status_code == 201
    assert result.json()["action"] == "QUARANTINE"
    assert result.json()["reason"] == "STALE_EVALUATION_PROFILE_VERSION"
    assert result.json()["profile_version_after"] == 1


def test_bootstrap_requires_two_reviewers_and_independent_admin(learning_api):
    client, transactions, _ = learning_api
    cases = [
        reviewed_case(client, item.transaction_id, index, "analyst1")
        for index, item in enumerate(transactions[:5])
    ]
    assert bootstrap(client, cases).status_code == 409

    admin_case = reviewed_case(client, transactions[5].transaction_id, 10, "admin")
    response = client.post(
        BASE + "/profile-learning/case",
        json={"case_id": admin_case, "expected_profile_version": None},
        headers=headers("admin", "self-authorize"),
    )
    assert response.status_code == 403


def test_profile_learning_rolls_back_profile_audit_outbox_and_response(
    learning_api, db_engine, monkeypatch
):
    client, transactions, _ = learning_api
    cases = [
        reviewed_case(client, item.transaction_id, index, f"analyst{index % 2 + 1}")
        for index, item in enumerate(transactions[:5])
    ]

    def fail(*args, **kwargs):
        raise RuntimeError("injected after profile and learning writes")

    with monkeypatch.context() as patch:
        patch.setattr(PostgresAuditRepository, "add", fail)
        assert bootstrap(client, cases).status_code == 500
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.profiles.get(transactions[0].customer_id, "KZT") is None
    with db_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM profile_learning_decisions WHERE customer_id=:id"),
                {"id": transactions[0].customer_id},
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text("""SELECT count(*) FROM profile_learning_evidence e JOIN
                profile_learning_decisions d USING (decision_id) WHERE d.customer_id=:id"""),
                {"id": transactions[0].customer_id},
            ).scalar_one()
            == 0
        )
    assert bootstrap(client, cases).status_code == 201


def test_learning_history_is_immutable_and_case_evidence_single_use(learning_api, db_engine):
    client, transactions, _ = learning_api
    cases = [
        reviewed_case(client, item.transaction_id, index, f"analyst{index % 2 + 1}")
        for index, item in enumerate(transactions[:5])
    ]
    result = bootstrap(client, cases)
    assert result.status_code == 201
    assert bootstrap(client, cases, "reuse-cases").status_code == 409
    for table in ("profile_learning_decisions", "profile_learning_evidence"):
        for statement in (
            f"UPDATE {table} SET decision_id=decision_id",
            f"DELETE FROM {table}",
            f"TRUNCATE {table} CASCADE",
        ):
            with pytest.raises(IntegrityError), db_engine.begin() as connection:
                connection.execute(text(statement))


def test_database_rejects_fabricated_verified_profile_provenance(learning_api, db_engine):
    client, transactions, _ = learning_api
    cases = [
        reviewed_case(client, item.transaction_id, index, f"analyst{index % 2 + 1}")
        for index, item in enumerate(transactions[:5])
    ]
    assert bootstrap(client, cases).status_code == 201
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            text("""UPDATE profiles SET version=version+1,
            admission_policy_version='fabricated',learning_decision_id=:decision
            WHERE customer_id=:customer AND currency='KZT'"""),
            {"decision": uuid4(), "customer": transactions[0].customer_id},
        )


def test_concurrent_case_updates_accept_only_one_profile_version(learning_api):
    client, transactions, _ = learning_api
    cases = [
        reviewed_case(client, item.transaction_id, index, f"analyst{index % 2 + 1}")
        for index, item in enumerate(transactions[:5])
    ]
    assert bootstrap(client, cases).status_code == 201
    case_a = reviewed_case(client, transactions[5].transaction_id, 5, "analyst1", profile_version=1)
    case_b = reviewed_case(client, transactions[8].transaction_id, 8, "analyst2", profile_version=1)

    def apply(case_id, key):
        return client.post(
            BASE + "/profile-learning/case",
            json={"case_id": case_id, "expected_profile_version": 1},
            headers=headers("admin", key),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda args: apply(*args), [(case_a, "race-a"), (case_b, "race-b")])
        )
    assert sorted(result.status_code for result in results) == [201, 409]


def test_concurrent_bootstraps_create_only_one_profile(learning_api):
    client, transactions, _ = learning_api
    first = [
        reviewed_case(client, item.transaction_id, index, f"analyst{index % 2 + 1}")
        for index, item in enumerate(transactions[:5])
    ]
    second = [
        reviewed_case(client, item.transaction_id, index + 30, f"analyst{index % 2 + 1}")
        for index, item in enumerate(transactions[7:12])
    ]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda args: bootstrap(client, *args),
                [(first, "bootstrap-a"), (second, "bootstrap-b")],
            )
        )
    assert sorted(result.status_code for result in results) == [201, 409]


def test_disabled_and_non_admin_fail_closed(learning_api, db_engine):
    client, transactions, entries = learning_api
    case_id = reviewed_case(client, transactions[0].transaction_id, 0, "analyst1")
    denied = client.post(
        BASE + "/profile-learning/case",
        json={"case_id": case_id, "expected_profile_version": None},
        headers=headers("analyst2", "denied"),
    )
    assert denied.status_code == 403
    config = Settings(
        environment="test",
        api_principals=json.dumps(entries),
        experimental_enabled=False,
        _env_file=None,
    )
    with TestClient(
        create_app(config, uow_factory=partial(create_unit_of_work, db_engine)),
        raise_server_exceptions=False,
    ) as disabled:
        response = disabled.post(
            BASE + "/profile-learning/case",
            json={"case_id": case_id, "expected_profile_version": None},
            headers=headers("admin", "disabled"),
        )
        assert response.status_code == 503
