"""A recovery claim never becomes permission without two bounded approvals."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from backend.app.identity.policy import HumanAccount
from backend.app.identity.recovery import (
    OperatorApproval,
    RecoveryCase,
    RecoveryDenied,
    RecoveryPurpose,
    require_two_operator_approvals,
)
from backend.app.shared.security import Role

NOW = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
DIGEST = "a" * 64


def _claims() -> tuple[
    RecoveryCase, HumanAccount, tuple[OperatorApproval, ...], tuple[HumanAccount, ...]
]:
    subject = HumanAccount(uuid4(), Role.ANALYST, active=False, authorization_version=4)
    case = RecoveryCase(
        uuid4(),
        subject.account_id,
        RecoveryPurpose.LOST_FACTORS,
        4,
        "INSTITUTION-2026/42",
        DIGEST,
        "d" * 64,
        NOW - timedelta(minutes=10),
        NOW + timedelta(minutes=5),
        NOW - timedelta(minutes=11),
    )

    def approval(operator: HumanAccount, credential_digest: str) -> OperatorApproval:
        return OperatorApproval(
            case.case_id,
            subject.account_id,
            case.purpose,
            case.proof_digest,
            case.action_sha256,
            operator.account_id,
            operator.authorization_version,
            uuid4(),
            uuid4(),
            credential_digest,
            NOW - timedelta(minutes=2),
        )

    operators = (HumanAccount(uuid4(), Role.ADMIN), HumanAccount(uuid4(), Role.ADMIN))
    return (
        case,
        subject,
        (
            approval(operators[0], "b" * 64),
            approval(operators[1], "c" * 64),
        ),
        operators,
    )


def test_two_bound_approvals_pass_policy_only() -> None:
    case, subject, approvals, operators = _claims()
    assert require_two_operator_approvals(case, subject, approvals, operators, NOW) is None


@pytest.mark.parametrize("count", [0, 1, 3])
def test_missing_or_extra_approvals_denied(count: int) -> None:
    case, subject, approvals, operators = _claims()
    supplied = (*approvals, approvals[0])[:count]
    with pytest.raises(RecoveryDenied):
        require_two_operator_approvals(case, subject, supplied, operators, NOW)


@pytest.mark.parametrize(
    "change",
    [
        {"operator_id": None},
        {"session_family_id": None},
        {"assertion_challenge_id": None},
        {"credential_id_sha256": None},
        {"operator_authorization_version": 2},
        {"proof_digest": "c" * 64},
        {"action_sha256": "e" * 64},
        {"purpose": RecoveryPurpose.FIRST_FACTOR_BOOTSTRAP},
        {"approved_at": NOW - timedelta(minutes=6)},
        {"approved_at": NOW + timedelta(seconds=1)},
    ],
)
def test_approval_identity_binding_and_freshness(change: dict[str, object]) -> None:
    case, subject, approvals, operators = _claims()
    if next(iter(change.values())) is None:
        name = next(iter(change))
        change[name] = getattr(approvals[0], name)
    with pytest.raises(RecoveryDenied):
        require_two_operator_approvals(
            case, subject, (approvals[0], replace(approvals[1], **change)), operators, NOW
        )


def test_subject_cannot_approve_own_recovery() -> None:
    case, subject, approvals, operators = _claims()
    with pytest.raises(RecoveryDenied):
        require_two_operator_approvals(
            case,
            subject,
            (approvals[0], replace(approvals[1], operator_id=subject.account_id)),
            operators,
            NOW,
        )


def test_subject_must_stay_frozen_at_exact_authorization_version() -> None:
    case, subject, approvals, operators = _claims()
    for altered in (replace(subject, active=True), replace(subject, authorization_version=5)):
        with pytest.raises(RecoveryDenied):
            require_two_operator_approvals(case, altered, approvals, operators, NOW)


def test_current_operator_state_is_authoritative() -> None:
    case, subject, approvals, operators = _claims()
    for altered in (
        replace(operators[1], active=False),
        replace(operators[1], role=Role.ANALYST),
        replace(operators[1], authorization_version=2),
        replace(operators[1], expires_at=NOW),
    ):
        with pytest.raises(RecoveryDenied):
            require_two_operator_approvals(case, subject, approvals, (operators[0], altered), NOW)


def test_duplicate_current_operator_is_denied() -> None:
    case, subject, approvals, operators = _claims()
    with pytest.raises(RecoveryDenied):
        require_two_operator_approvals(case, subject, approvals, (operators[0], operators[0]), NOW)


def test_expired_proof_and_changed_case_are_denied() -> None:
    case, subject, approvals, operators = _claims()
    with pytest.raises(RecoveryDenied):
        require_two_operator_approvals(case, subject, approvals, operators, case.proof_expires_at)
    with pytest.raises(RecoveryDenied):
        require_two_operator_approvals(
            replace(case, case_id=uuid4()), subject, approvals, operators, NOW
        )


def test_approval_before_proof_is_denied() -> None:
    case, subject, approvals, operators = _claims()
    with pytest.raises(RecoveryDenied):
        require_two_operator_approvals(
            case,
            subject,
            (
                approvals[0],
                replace(approvals[1], approved_at=case.proof_verified_at - timedelta(seconds=1)),
            ),
            operators,
            NOW,
        )


def test_proof_window_cannot_be_extended() -> None:
    case, _, _, _ = _claims()
    with pytest.raises(ValueError, match="bounded"):
        replace(case, proof_expires_at=case.proof_verified_at + timedelta(minutes=16))
