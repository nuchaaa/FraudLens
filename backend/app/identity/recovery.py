"""Fail-closed policy for future supervised identity recovery.

These records are *claims*, not authentication. A future adapter must verify the
institutional proof and each operator's fresh WebAuthn assertion before passing
them here. No production recovery endpoint or persistence workflow uses this yet.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from backend.app.identity.policy import HumanAccount
from backend.app.shared.security import Role
from backend.app.shared.validation import utc

_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{5,95}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
PROOF_MAX_AGE = timedelta(minutes=15)
APPROVAL_MAX_AGE = timedelta(minutes=5)


class RecoveryPurpose(StrEnum):
    FIRST_FACTOR_BOOTSTRAP = "FIRST_FACTOR_BOOTSTRAP"
    LOST_FACTORS = "LOST_FACTORS"
    ADMIN_FACTOR_CHANGE = "ADMIN_FACTOR_CHANGE"


class RecoveryDenied(ValueError):
    """The supplied claims do not meet the recovery policy."""


@dataclass(frozen=True)
class RecoveryCase:
    case_id: UUID
    subject_id: UUID
    purpose: RecoveryPurpose
    subject_authorization_version: int
    reference: str
    proof_digest: str
    action_sha256: str
    proof_verified_at: datetime
    proof_expires_at: datetime
    frozen_at: datetime

    def __post_init__(self) -> None:
        for name in ("proof_verified_at", "proof_expires_at", "frozen_at"):
            object.__setattr__(self, name, utc(getattr(self, name)))
        if (
            not _REFERENCE.fullmatch(self.reference)
            or not _DIGEST.fullmatch(self.proof_digest)
            or not _DIGEST.fullmatch(self.action_sha256)
            or self.subject_authorization_version < 1
            or self.proof_expires_at <= self.proof_verified_at
            or self.proof_expires_at - self.proof_verified_at > PROOF_MAX_AGE
            or self.frozen_at > self.proof_verified_at
            or self.frozen_at >= self.proof_expires_at
        ):
            raise ValueError("invalid bounded recovery case")


@dataclass(frozen=True)
class OperatorApproval:
    case_id: UUID
    subject_id: UUID
    purpose: RecoveryPurpose
    proof_digest: str
    action_sha256: str
    operator_id: UUID
    operator_authorization_version: int
    session_family_id: UUID
    assertion_challenge_id: UUID
    credential_id_sha256: str
    approved_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "approved_at", utc(self.approved_at))
        if (
            not _DIGEST.fullmatch(self.proof_digest)
            or not _DIGEST.fullmatch(self.action_sha256)
            or not _DIGEST.fullmatch(self.credential_id_sha256)
            or type(self.operator_authorization_version) is not int
            or self.operator_authorization_version < 1
        ):
            raise ValueError("invalid approval evidence digest")


def require_two_operator_approvals(
    case: RecoveryCase,
    subject: HumanAccount,
    approvals: tuple[OperatorApproval, ...],
    operators: tuple[HumanAccount, ...],
    now: datetime,
) -> None:
    """Validate bound, fresh, distinct approval claims; do not execute recovery.

    Authentication, proof verification, recovery-specific freeze persistence,
    uniqueness and
    one-use consumption must be established by the eventual transactional workflow.
    """
    now = utc(now)
    if (
        now >= case.proof_expires_at
        or now < case.frozen_at
        or subject.account_id != case.subject_id
        or subject.active
        or subject.authorization_version != case.subject_authorization_version
        or len(approvals) != 2
        or len(operators) != 2
    ):
        raise RecoveryDenied("recovery prerequisites unavailable")
    if len({approval.operator_id for approval in approvals}) != 2:
        raise RecoveryDenied("two distinct operators required")
    current_operators = {account.account_id: account for account in operators}
    if len(current_operators) != 2:
        raise RecoveryDenied("two distinct current operators required")
    if (
        len({approval.session_family_id for approval in approvals}) != 2
        or len({approval.assertion_challenge_id for approval in approvals}) != 2
        or len({approval.credential_id_sha256 for approval in approvals}) != 2
    ):
        raise RecoveryDenied("independent fresh assertions required")
    for approval in approvals:
        operator = current_operators.get(approval.operator_id)
        if (
            approval.case_id != case.case_id
            or approval.subject_id != case.subject_id
            or approval.purpose != case.purpose
            or approval.proof_digest != case.proof_digest
            or approval.action_sha256 != case.action_sha256
            or approval.operator_id == case.subject_id
            or operator is None
            or operator.role != Role.ADMIN
            or not operator.enabled_at(now)
            or operator.authorization_version != approval.operator_authorization_version
            or approval.approved_at < case.proof_verified_at
            or approval.approved_at > now
            or now - approval.approved_at > APPROVAL_MAX_AGE
        ):
            raise RecoveryDenied("approval is stale, unauthorized or unbound")
