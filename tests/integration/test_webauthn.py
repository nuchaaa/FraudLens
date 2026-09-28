"""Real PostgreSQL ceremonies with software-generated authenticator signatures."""

import base64
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from functools import partial
from uuid import uuid4

import cbor2
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy import exc, text

from backend.adapters.database.uow import create_unit_of_work
from backend.app.identity import service as identity_service
from backend.app.identity.service import AuthenticationDenied
from backend.app.shared.security import Role
from backend.config import Settings
from backend.main import create_app

pytestmark = pytest.mark.postgres
ORIGIN = "http://127.0.0.1:5173"
RP_ID = "127.0.0.1"
PASSWORD = "A long WebAuthn test password"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _registration(challenge: str, key: ec.EllipticCurvePrivateKey, credential_id: bytes) -> dict:
    public = key.public_key().public_numbers()
    cose = cbor2.dumps(
        {1: 2, 3: -7, -1: 1, -2: public.x.to_bytes(32, "big"), -3: public.y.to_bytes(32, "big")}
    )
    auth_data = (
        hashlib.sha256(RP_ID.encode()).digest()
        + bytes([0x45])  # user present, user verified, attested credential data
        + (0).to_bytes(4, "big")
        + bytes(16)
        + len(credential_id).to_bytes(2, "big")
        + credential_id
        + cose
    )
    client = json.dumps(
        {"type": "webauthn.create", "challenge": challenge, "origin": ORIGIN},
        separators=(",", ":"),
    ).encode()
    return {
        "id": _b64(credential_id),
        "rawId": _b64(credential_id),
        "type": "public-key",
        "response": {
            "clientDataJSON": _b64(client),
            "attestationObject": _b64(
                cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
            ),
        },
        "clientExtensionResults": {},
    }


def _assertion(
    challenge: str,
    key: ec.EllipticCurvePrivateKey,
    credential_id: bytes,
    *,
    origin: str = ORIGIN,
    sign_count: int = 1,
) -> dict:
    client = json.dumps(
        {"type": "webauthn.get", "challenge": challenge, "origin": origin},
        separators=(",", ":"),
    ).encode()
    auth_data = (
        hashlib.sha256(RP_ID.encode()).digest()
        + bytes([0x05])  # user present and verified
        + sign_count.to_bytes(4, "big")
    )
    signature = key.sign(auth_data + hashlib.sha256(client).digest(), ec.ECDSA(hashes.SHA256()))
    return {
        "id": _b64(credential_id),
        "rawId": _b64(credential_id),
        "type": "public-key",
        "response": {
            "clientDataJSON": _b64(client),
            "authenticatorData": _b64(auth_data),
            "signature": _b64(signature),
            "userHandle": None,
        },
        "clientExtensionResults": {},
    }


@pytest.fixture
def mfa_browser(db_engine):
    app = create_app(
        Settings(
            environment="test",
            human_auth_enabled=True,
            human_origin=ORIGIN,
            human_local_insecure=True,
            _env_file=None,
        ),
        uow_factory=partial(create_unit_of_work, db_engine),
    )
    with TestClient(app, base_url=ORIGIN) as client:
        identity = app.state.services.identity
        assert identity is not None
        yield client, identity, db_engine


def _enroll(client, identity):
    login_name = f"key-analyst-{uuid4().hex[:8]}"
    account_id = identity.provision(
        login_name, PASSWORD, Role.ANALYST, frozenset({uuid4()}), operator_id=uuid4()
    )
    login = client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"login": login_name, "password": PASSWORD},
    )
    assert login.status_code == 200
    csrf = login.json()["csrf"]
    options = client.post(
        "/api/v1/auth/mfa/first-factor/options",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={"password": PASSWORD},
    )
    assert options.status_code == 200
    key = ec.generate_private_key(ec.SECP256R1())
    credential_id = uuid4().bytes
    response = _registration(options.json()["public_key"]["challenge"], key, credential_id)
    completed = client.post(
        "/api/v1/auth/mfa/first-factor/verify",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={"challenge_id": options.json()["challenge_id"], "credential": response},
    )
    assert completed.status_code == 201, completed.text
    assert client.get("/api/v1/auth/session").status_code == 401
    return account_id, login_name, key, credential_id


def test_first_factor_requires_fresh_password_and_mfa_login_consumes_once(mfa_browser):
    client, identity, db_engine = mfa_browser
    account_id, login_name, key, credential_id = _enroll(client, identity)
    assert (
        client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"login": login_name, "password": PASSWORD},
        ).status_code
        == 401
    )
    started = client.post(
        "/api/v1/auth/mfa/login/options",
        headers={"Origin": ORIGIN},
        json={"login": login_name, "password": PASSWORD},
    )
    assert started.status_code == 200
    assert not started.headers.get_list("set-cookie")
    challenge_id = started.json()["challenge_id"]
    assertion = _assertion(started.json()["public_key"]["challenge"], key, credential_id)
    finished = client.post(
        "/api/v1/auth/mfa/login/verify",
        headers={"Origin": ORIGIN},
        json={"challenge_id": challenge_id, "credential": assertion},
    )
    assert finished.status_code == 200, finished.text
    assert finished.json()["account_id"] == str(account_id)
    assert client.get("/api/v1/auth/session").status_code == 200
    replay = client.post(
        "/api/v1/auth/mfa/login/verify",
        headers={"Origin": ORIGIN},
        json={"challenge_id": challenge_id, "credential": assertion},
    )
    assert replay.status_code == 401
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM human_sessions "
                    "WHERE account_id=:id AND revoked_at IS NULL"
                ),
                {"id": account_id},
            )
            == 1
        )


def test_wrong_origin_and_bad_signature_consume_challenge(mfa_browser):
    client, identity, _ = mfa_browser
    _, login_name, key, credential_id = _enroll(client, identity)
    started = client.post(
        "/api/v1/auth/mfa/login/options",
        headers={"Origin": ORIGIN},
        json={"login": login_name, "password": PASSWORD},
    ).json()
    wrong = _assertion(
        started["public_key"]["challenge"], key, credential_id, origin="https://evil.test"
    )
    for assertion in (wrong, _assertion(started["public_key"]["challenge"], key, credential_id)):
        denied = client.post(
            "/api/v1/auth/mfa/login/verify",
            headers={"Origin": ORIGIN},
            json={"challenge_id": started["challenge_id"], "credential": assertion},
        )
        assert denied.status_code == 401


def test_same_challenge_cannot_create_two_sessions(mfa_browser):
    client, identity, _ = mfa_browser
    _, login_name, key, credential_id = _enroll(client, identity)
    started = identity.start_mfa_login(login_name, PASSWORD)
    assertion = _assertion(started.options["challenge"], key, credential_id)

    def attempt() -> bool:
        try:
            identity.finish_mfa_login(started.challenge_id, assertion)
            return True
        except AuthenticationDenied:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: attempt(), range(2))) == [False, True]


def test_failed_enrollment_consumes_challenge_and_keeps_password_session(mfa_browser):
    client, identity, db_engine = mfa_browser
    login_name = f"key-analyst-{uuid4().hex[:8]}"
    account_id = identity.provision(
        login_name, PASSWORD, Role.ANALYST, frozenset({uuid4()}), operator_id=uuid4()
    )
    login = client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"login": login_name, "password": PASSWORD},
    )
    csrf = login.json()["csrf"]
    started = client.post(
        "/api/v1/auth/mfa/first-factor/options",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={"password": PASSWORD},
    ).json()
    key = ec.generate_private_key(ec.SECP256R1())
    response = _registration(started["public_key"]["challenge"], key, uuid4().bytes)
    response["response"]["clientDataJSON"] = _b64(b"invalid")
    attempt = {
        "challenge_id": started["challenge_id"],
        "credential": response,
    }
    for _ in range(2):
        result = client.post(
            "/api/v1/auth/mfa/first-factor/verify",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json=attempt,
        )
        assert result.status_code == 401
    assert client.get("/api/v1/auth/session").status_code == 200
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM human_authenticators WHERE account_id=:id"),
                {"id": account_id},
            )
            == 0
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM human_mfa_challenges "
                    "WHERE challenge_id=:id AND consumed_at IS NOT NULL"
                ),
                {"id": started["challenge_id"]},
            )
            == 1
        )


def test_sign_counter_reuse_and_disabled_account_cannot_log_in(mfa_browser):
    client, identity, db_engine = mfa_browser
    account_id, login_name, key, credential_id = _enroll(client, identity)

    def start():
        response = client.post(
            "/api/v1/auth/mfa/login/options",
            headers={"Origin": ORIGIN},
            json={"login": login_name, "password": PASSWORD},
        )
        assert response.status_code == 200
        return response.json()

    first = start()
    assert (
        client.post(
            "/api/v1/auth/mfa/login/verify",
            headers={"Origin": ORIGIN},
            json={
                "challenge_id": first["challenge_id"],
                "credential": _assertion(first["public_key"]["challenge"], key, credential_id),
            },
        ).status_code
        == 200
    )
    second = start()
    assert (
        client.post(
            "/api/v1/auth/mfa/login/verify",
            headers={"Origin": ORIGIN},
            json={
                "challenge_id": second["challenge_id"],
                "credential": _assertion(second["public_key"]["challenge"], key, credential_id),
            },
        ).status_code
        == 401
    )
    third = start()
    identity.change(account_id, operator_id=uuid4(), active=False)
    assert (
        client.post(
            "/api/v1/auth/mfa/login/verify",
            headers={"Origin": ORIGIN},
            json={
                "challenge_id": third["challenge_id"],
                "credential": _assertion(
                    third["public_key"]["challenge"], key, credential_id, sign_count=2
                ),
            },
        ).status_code
        == 401
    )
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM human_mfa_challenges "
                    "WHERE challenge_id=:id AND consumed_at IS NOT NULL"
                ),
                {"id": third["challenge_id"]},
            )
            == 1
        )


def test_additional_factor_requires_password_existing_assertion_and_revokes_sessions(
    mfa_browser,
):
    client, identity, db_engine = mfa_browser
    account_id, login_name, key, credential_id = _enroll(client, identity)
    login_options = client.post(
        "/api/v1/auth/mfa/login/options",
        headers={"Origin": ORIGIN},
        json={"login": login_name, "password": PASSWORD},
    ).json()
    login = client.post(
        "/api/v1/auth/mfa/login/verify",
        headers={"Origin": ORIGIN},
        json={
            "challenge_id": login_options["challenge_id"],
            "credential": _assertion(login_options["public_key"]["challenge"], key, credential_id),
        },
    )
    assert login.status_code == 200
    csrf = login.json()["csrf"]
    assert (
        client.post(
            "/api/v1/auth/mfa/add-factor/options",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={"password": "wrong password"},
        ).status_code
        == 401
    )
    started = client.post(
        "/api/v1/auth/mfa/add-factor/options",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={"password": PASSWORD},
    )
    assert started.status_code == 200
    proof = client.post(
        "/api/v1/auth/mfa/add-factor/proof",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={
            "challenge_id": started.json()["challenge_id"],
            "credential": _assertion(
                started.json()["public_key"]["challenge"],
                key,
                credential_id,
                sign_count=2,
            ),
        },
    )
    assert proof.status_code == 200, proof.text
    new_key = ec.generate_private_key(ec.SECP256R1())
    new_id = uuid4().bytes
    finished = client.post(
        "/api/v1/auth/mfa/add-factor/verify",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={
            "challenge_id": proof.json()["challenge_id"],
            "credential": _registration(proof.json()["public_key"]["challenge"], new_key, new_id),
        },
    )
    assert finished.status_code == 201, finished.text
    assert client.get("/api/v1/auth/session").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/mfa/add-factor/verify",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "challenge_id": proof.json()["challenge_id"],
                "credential": _registration(
                    proof.json()["public_key"]["challenge"], new_key, new_id
                ),
            },
        ).status_code
        == 401
    )
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM human_authenticators "
                    "WHERE account_id=:id AND revoked_at IS NULL"
                ),
                {"id": account_id},
            )
            == 2
        )
    for candidate_key, candidate_id, count in (
        (key, credential_id, 3),
        (new_key, new_id, 1),
    ):
        options = client.post(
            "/api/v1/auth/mfa/login/options",
            headers={"Origin": ORIGIN},
            json={"login": login_name, "password": PASSWORD},
        ).json()
        assert (
            client.post(
                "/api/v1/auth/mfa/login/verify",
                headers={"Origin": ORIGIN},
                json={
                    "challenge_id": options["challenge_id"],
                    "credential": _assertion(
                        options["public_key"]["challenge"],
                        candidate_key,
                        candidate_id,
                        sign_count=count,
                    ),
                },
            ).status_code
            == 200
        )


def test_remove_factor_requires_another_key_and_preserves_last_factor(mfa_browser):
    _, identity, db_engine = mfa_browser
    account_id, login_name, first_key, first_id = _enroll(mfa_browser[0], identity)
    first_login = identity.start_mfa_login(login_name, PASSWORD)
    session = identity.finish_mfa_login(
        first_login.challenge_id,
        _assertion(first_login.options["challenge"], first_key, first_id),
    )
    proof = identity.start_add_factor(session.access, session.csrf, session.csrf, PASSWORD)
    registration = identity.finish_add_factor_proof(
        session.access,
        session.csrf,
        session.csrf,
        proof.challenge_id,
        _assertion(proof.options["challenge"], first_key, first_id, sign_count=2),
    )
    second_key = ec.generate_private_key(ec.SECP256R1())
    second_id = uuid4().bytes
    identity.finish_add_factor(
        session.access,
        session.csrf,
        session.csrf,
        registration.challenge_id,
        _registration(registration.options["challenge"], second_key, second_id),
    )
    next_login = identity.start_mfa_login(login_name, PASSWORD)
    current = identity.finish_mfa_login(
        next_login.challenge_id,
        _assertion(next_login.options["challenge"], first_key, first_id, sign_count=3),
    )
    assert len(identity.list_factors(current.access, current.csrf)) == 2
    remove = identity.start_remove_factor(
        current.access, current.csrf, current.csrf, PASSWORD, _b64(first_id)
    )
    with pytest.raises(AuthenticationDenied):
        identity.finish_remove_factor(
            current.access,
            current.csrf,
            current.csrf,
            remove.challenge_id,
            _assertion(remove.options["challenge"], first_key, first_id, sign_count=4),
        )
    with pytest.raises(AuthenticationDenied):
        identity.finish_remove_factor(
            current.access,
            current.csrf,
            current.csrf,
            remove.challenge_id,
            _assertion(remove.options["challenge"], second_key, second_id),
        )
    fresh = identity.start_remove_factor(
        current.access, current.csrf, current.csrf, PASSWORD, _b64(first_id)
    )
    identity.finish_remove_factor(
        current.access,
        current.csrf,
        current.csrf,
        fresh.challenge_id,
        _assertion(fresh.options["challenge"], second_key, second_id),
    )
    with pytest.raises(AuthenticationDenied):
        identity.list_factors(current.access, current.csrf)
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM human_authenticators "
                    "WHERE account_id=:id AND revoked_at IS NULL"
                ),
                {"id": account_id},
            )
            == 1
        )
    final_login = identity.start_mfa_login(login_name, PASSWORD)
    after = identity.finish_mfa_login(
        final_login.challenge_id,
        _assertion(final_login.options["challenge"], second_key, second_id, sign_count=2),
    )
    with pytest.raises(AuthenticationDenied):
        identity.start_remove_factor(
            after.access, after.csrf, after.csrf, PASSWORD, _b64(second_id)
        )


def test_add_factor_proof_is_bound_to_its_session_family(mfa_browser):
    client, identity, db_engine = mfa_browser
    account_id, login_name, key, credential_id = _enroll(client, identity)
    first = identity.start_mfa_login(login_name, PASSWORD)
    session_a = identity.finish_mfa_login(
        first.challenge_id, _assertion(first.options["challenge"], key, credential_id)
    )
    second = identity.start_mfa_login(login_name, PASSWORD)
    session_b = identity.finish_mfa_login(
        second.challenge_id,
        _assertion(second.options["challenge"], key, credential_id, sign_count=2),
    )
    proof = identity.start_add_factor(session_a.access, session_a.csrf, session_a.csrf, PASSWORD)
    assertion = _assertion(proof.options["challenge"], key, credential_id, sign_count=3)
    with pytest.raises(AuthenticationDenied):
        identity.finish_add_factor_proof(
            session_b.access, session_b.csrf, session_b.csrf, proof.challenge_id, assertion
        )
    with pytest.raises(AuthenticationDenied):
        identity.finish_add_factor_proof(
            session_a.access, session_a.csrf, session_a.csrf, proof.challenge_id, assertion
        )
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM human_mfa_challenges "
                    "WHERE account_id=:id AND ceremony='ADD_FACTOR_REGISTER'"
                ),
                {"id": account_id},
            )
            == 0
        )


def test_first_factor_is_bound_to_the_starting_session(mfa_browser):
    _, identity, _ = mfa_browser
    login_name = f"key-analyst-{uuid4().hex[:8]}"
    identity.provision(
        login_name, PASSWORD, Role.ANALYST, frozenset({uuid4()}), operator_id=uuid4()
    )
    first = identity.login(login_name, PASSWORD)
    second = identity.login(login_name, PASSWORD)
    started = identity.start_first_factor(first.access, first.csrf, first.csrf, PASSWORD)
    key = ec.generate_private_key(ec.SECP256R1())
    registration = _registration(started.options["challenge"], key, uuid4().bytes)
    with pytest.raises(AuthenticationDenied):
        identity.finish_first_factor(
            second.access, second.csrf, second.csrf, started.challenge_id, registration
        )
    identity.finish_first_factor(
        first.access, first.csrf, first.csrf, started.challenge_id, registration
    )
    assert identity.session(first.access, first.csrf) is None
    assert identity.session(second.access, second.csrf) is None


def test_expired_challenge_retention_prunes_only_after_one_day(mfa_browser):
    client, identity, db_engine = mfa_browser
    account_id, login_name, _, _ = _enroll(client, identity)
    old_id = uuid4()
    created = datetime.now(UTC) - timedelta(days=2)
    with db_engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO human_mfa_challenges
                (challenge_id,account_id,ceremony,challenge,rp_id,origin,
                 authorization_version,created_at,expires_at)
                VALUES (:id,:account,'LOGIN',:challenge,:rp,:origin,2,:created,:expires)"""),
            {
                "id": old_id,
                "account": account_id,
                "challenge": uuid4().bytes + uuid4().bytes,
                "rp": RP_ID,
                "origin": ORIGIN,
                "created": created,
                "expires": created + timedelta(minutes=2),
            },
        )
        recent_id = connection.scalar(
            text(
                "SELECT challenge_id FROM human_mfa_challenges "
                "WHERE account_id=:id AND ceremony='FIRST_ENROLLMENT'"
            ),
            {"id": account_id},
        )
    with pytest.raises(exc.IntegrityError), db_engine.begin() as connection:
        connection.execute(
            text("DELETE FROM human_mfa_challenges WHERE challenge_id=:id"),
            {"id": recent_id},
        )
    identity.start_mfa_login(login_name, PASSWORD)
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM human_mfa_challenges WHERE challenge_id=:id"),
                {"id": old_id},
            )
            == 0
        )
        assert (
            connection.scalar(
                text("SELECT count(*) FROM human_mfa_challenges WHERE challenge_id=:id"),
                {"id": recent_id},
            )
            == 1
        )


def test_add_factor_rolls_back_if_audit_fails_then_completes_once(mfa_browser, monkeypatch):
    client, identity, db_engine = mfa_browser
    account_id, login_name, first_key, first_id = _enroll(client, identity)
    login = identity.start_mfa_login(login_name, PASSWORD)
    session = identity.finish_mfa_login(
        login.challenge_id, _assertion(login.options["challenge"], first_key, first_id)
    )
    proof = identity.start_add_factor(session.access, session.csrf, session.csrf, PASSWORD)
    registration = identity.finish_add_factor_proof(
        session.access,
        session.csrf,
        session.csrf,
        proof.challenge_id,
        _assertion(proof.options["challenge"], first_key, first_id, sign_count=2),
    )
    second_key = ec.generate_private_key(ec.SECP256R1())
    second_id = uuid4().bytes
    response = _registration(registration.options["challenge"], second_key, second_id)
    original = identity_service._audit

    def fail_added(*args, **kwargs):
        if args[2] == "HUMAN_MFA_FACTOR_ADDED":
            raise RuntimeError("simulated audit failure")
        return original(*args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(identity_service, "_audit", fail_added)
        with pytest.raises(RuntimeError, match="simulated audit failure"):
            identity.finish_add_factor(
                session.access,
                session.csrf,
                session.csrf,
                registration.challenge_id,
                response,
            )
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT consumed_at FROM human_mfa_challenges WHERE challenge_id=:id"),
                {"id": registration.challenge_id},
            )
            is None
        )
        assert (
            connection.scalar(
                text("SELECT count(*) FROM human_authenticators WHERE account_id=:id"),
                {"id": account_id},
            )
            == 1
        )
    assert identity.session(session.access, session.csrf) is not None

    def attempt() -> bool:
        try:
            identity.finish_add_factor(
                session.access,
                session.csrf,
                session.csrf,
                registration.challenge_id,
                response,
            )
            return True
        except AuthenticationDenied:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: attempt(), range(2))) == [False, True]
    assert identity.session(session.access, session.csrf) is None
