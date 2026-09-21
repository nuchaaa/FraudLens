"""Separately authorized, append-only profile learning decisions."""

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from statistics import median
from uuid import UUID, uuid4

from backend.app.audit.entities import AuditEvent
from backend.app.cases.entities import CaseState, FraudCase
from backend.app.evaluation.contracts import EvaluationRecord, ReviewFeedback
from backend.app.evaluation.service import authorized_evaluation, digest
from backend.app.feedback.entities import AnalystVerdict
from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation
from backend.app.profile.gate import GatePolicy, ProfileUpdateAction, ProfileUpdateGate
from backend.app.shared.errors import ConcurrentUpdate, HistoryConflict
from backend.app.shared.events import DomainEvent, EventType
from backend.app.shared.ports import UnitOfWork
from backend.app.shared.security import Forbidden, NotFound, Principal, Role
from backend.app.transaction.entities import Transaction
from backend.app.transaction.idempotency import IdempotencyRecord
from backend.app.transaction.service import (
    SubmissionResult,
    UnitOfWorkFactory,
    validate_idempotency_key,
)

POLICY_VERSION = "profile-learning-v1-experimental"
MINIMUM_BOOTSTRAP_OBSERVATIONS = 5
MINIMUM_BOOTSTRAP_REVIEWERS = 2
MAXIMUM_BOOTSTRAP_OBSERVATIONS = 100


class LearningInputError(ValueError):
    pass


class LearningKind(StrEnum):
    CASE_UPDATE = "CASE_UPDATE"
    BOOTSTRAP = "BOOTSTRAP"


@dataclass(frozen=True)
class LearningEvidence:
    case_id: UUID
    feedback_id: UUID
    transaction_id: UUID
    reviewer_id: UUID


@dataclass(frozen=True)
class LearningDecision:
    decision_id: UUID
    customer_id: UUID
    currency: str
    actor_id: UUID
    kind: LearningKind
    action: ProfileUpdateAction
    reason: str
    policy_version: str
    profile_version_before: int | None
    profile_version_after: int | None
    created_at: datetime
    response_json: str
    evidence: tuple[LearningEvidence, ...]


def _require_admin(principal: Principal) -> None:
    if Role.ADMIN not in principal.roles:
        raise Forbidden("profile learning authorization requires admin role")


def _terminal_evidence(
    uow: UnitOfWork, principal: Principal, case_id: UUID, *, lock: bool
) -> tuple[FraudCase, ReviewFeedback, Transaction, EvaluationRecord]:
    case = uow.reviews.get(case_id, lock=lock)
    if case is None:
        raise NotFound("case not found")
    evaluation = authorized_evaluation(uow, principal, case.assessment_id)
    if case.state != CaseState.CLOSED:
        raise HistoryConflict("profile learning requires a closed case")
    terminal = tuple(
        item
        for item in uow.reviews.feedback(case_id)
        if item.verdict in {AnalystVerdict.LEGITIMATE, AnalystVerdict.CONFIRMED_FRAUD}
    )
    if len(terminal) != 1:
        raise HistoryConflict("case needs exactly one terminal feedback record")
    if terminal[0].actor_id == principal.principal_id:
        raise Forbidden("learning authorizer must be independent from the reviewer")
    transaction = uow.transactions.get(evaluation.transaction_id)
    if transaction is None:
        raise NotFound("transaction not found")
    return case, terminal[0], transaction, evaluation


def _captured_profile_version(evaluation: EvaluationRecord) -> int | None:
    value = json.loads(evaluation.response_json)["risk"]["profile_version"]
    if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 1):
        raise HistoryConflict("evaluation has invalid captured profile provenance")
    return value


def _response(
    identifier: UUID,
    customer_id: UUID,
    currency: str,
    actor_id: UUID,
    kind: LearningKind,
    action: ProfileUpdateAction,
    reason: str,
    before: int | None,
    after: int | None,
    created_at: datetime,
    evidence: tuple[LearningEvidence, ...],
) -> str:
    return json.dumps(
        {
            "schema_version": "profile-learning-decision-v1",
            "decision_id": str(identifier),
            "customer_id": str(customer_id),
            "currency": currency,
            "actor_id": str(actor_id),
            "kind": kind.value,
            "action": action.value,
            "reason": reason,
            "policy_version": POLICY_VERSION,
            "profile_version_before": before,
            "profile_version_after": after,
            "created_at": created_at.isoformat(),
            "evidence": [
                {
                    "case_id": str(item.case_id),
                    "feedback_id": str(item.feedback_id),
                    "transaction_id": str(item.transaction_id),
                    "reviewer_id": str(item.reviewer_id),
                }
                for item in evidence
            ],
            "admission_workflow_verified": action == ProfileUpdateAction.ACCEPT,
            "low_weight_applied": False,
            "correction_applied": False,
            "experimental": True,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class ProfileLearningService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self.uow_factory = uow_factory

    def apply_case(
        self,
        principal: Principal,
        key: str,
        case_id: UUID,
        *,
        expected_profile_version: int | None,
    ) -> SubmissionResult:
        _require_admin(principal)
        validate_idempotency_key(key)
        request_hash = digest(
            "profile-learning-case",
            {"case_id": str(case_id), "expected_profile_version": expected_profile_version},
        )
        with self.uow_factory() as uow:
            _, _, initial_tx, _ = _terminal_evidence(uow, principal, case_id, lock=False)
            prior = uow.idempotency.acquire(principal.principal_id, key, request_hash)
            if prior:
                return SubmissionResult(prior.response_json, prior.status_code, True)
            _, feedback, transaction, evaluation = _terminal_evidence(
                uow, principal, case_id, lock=True
            )
            profile = uow.profiles.get_for_update(transaction.customer_id, transaction.currency)
            current_version = profile.version if profile else None
            if current_version != expected_profile_version:
                raise ConcurrentUpdate("profile version changed")
            identifier, created_at = uuid4(), datetime.now(UTC)
            if feedback.verdict == AnalystVerdict.CONFIRMED_FRAUD:
                action, reason, updated = (
                    ProfileUpdateAction.REJECT_FROM_PROFILE,
                    "CONFIRMED_FRAUD",
                    profile,
                )
            elif profile is None:
                action, reason, updated = (
                    ProfileUpdateAction.QUARANTINE,
                    "COLD_START_REQUIRES_BOOTSTRAP",
                    None,
                )
            elif not profile.admission_workflow_verified:
                action, reason, updated = (
                    ProfileUpdateAction.QUARANTINE,
                    "UNVERIFIED_PROFILE_PROVENANCE",
                    profile,
                )
            elif transaction.timestamp < profile.as_of:
                action, reason, updated = (
                    ProfileUpdateAction.QUARANTINE,
                    "LATE_REVIEW_REQUIRES_REPLAY",
                    profile,
                )
            elif _captured_profile_version(evaluation) != profile.version:
                action, reason, updated = (
                    ProfileUpdateAction.QUARANTINE,
                    "STALE_EVALUATION_PROFILE_VERSION",
                    profile,
                )
            else:
                gate_decision, candidate = ProfileUpdateGate().apply(
                    transaction, profile, AnalystVerdict.LEGITIMATE
                )
                action, reason, updated = gate_decision.action, gate_decision.reason, candidate
            after = current_version
            if action == ProfileUpdateAction.ACCEPT:
                assert updated is not None and profile is not None
                updated = replace(
                    updated,
                    admission_workflow_verified=True,
                    admission_policy_version=POLICY_VERSION,
                    learning_decision_id=identifier,
                )
                uow.profiles.save(updated, expected_version=profile.version)
                after = updated.version
            evidence = (
                LearningEvidence(
                    case_id,
                    feedback.feedback_id,
                    transaction.transaction_id,
                    feedback.actor_id,
                ),
            )
            return self._finish(
                uow,
                principal,
                key,
                request_hash,
                initial_tx.transaction_id,
                identifier,
                transaction.customer_id,
                transaction.currency,
                LearningKind.CASE_UPDATE,
                action,
                reason,
                current_version,
                after,
                created_at,
                evidence,
            )

    def bootstrap(
        self,
        principal: Principal,
        key: str,
        case_ids: tuple[UUID, ...],
    ) -> SubmissionResult:
        _require_admin(principal)
        validate_idempotency_key(key)
        if not MINIMUM_BOOTSTRAP_OBSERVATIONS <= len(case_ids) <= MAXIMUM_BOOTSTRAP_OBSERVATIONS:
            raise LearningInputError("bootstrap case count is outside policy")
        if len(set(case_ids)) != len(case_ids):
            raise LearningInputError("bootstrap cases must be unique")
        ordered_ids = tuple(sorted(case_ids, key=str))
        request_hash = digest("profile-learning-bootstrap", [str(item) for item in ordered_ids])
        with self.uow_factory() as uow:
            initial = [_terminal_evidence(uow, principal, item, lock=False) for item in ordered_ids]
            initial_tx = initial[0][2]
            prior = uow.idempotency.acquire(principal.principal_id, key, request_hash)
            if prior:
                return SubmissionResult(prior.response_json, prior.status_code, True)
            collected = [
                _terminal_evidence(uow, principal, item, lock=True) for item in ordered_ids
            ]
            feedback = tuple(item[1] for item in collected)
            transactions = tuple(item[2] for item in collected)
            evaluations = tuple(item[3] for item in collected)
            if any(item.verdict != AnalystVerdict.LEGITIMATE for item in feedback):
                raise HistoryConflict("bootstrap requires legitimate terminal feedback")
            if any(_captured_profile_version(item) is not None for item in evaluations):
                raise HistoryConflict("bootstrap requires evaluations captured without a profile")
            if len({item.actor_id for item in feedback}) < MINIMUM_BOOTSTRAP_REVIEWERS:
                raise HistoryConflict("bootstrap requires at least two independent reviewers")
            identity = {(item.customer_id, item.currency) for item in transactions}
            if len(identity) != 1:
                raise HistoryConflict("bootstrap transactions must share customer and currency")
            customer_id, currency = identity.pop()
            if uow.profiles.get_for_update(customer_id, currency) is not None:
                raise ConcurrentUpdate("profile already exists")
            customer = uow.customers.get(customer_id)
            if customer is None:
                raise NotFound("customer not found")
            ordered = tuple(
                sorted(transactions, key=lambda item: (item.timestamp, str(item.transaction_id)))
            )
            if ordered[0].timestamp <= ordered[-1].timestamp - timedelta(days=180):
                raise HistoryConflict("bootstrap observations must fit the active long window")
            center = Decimal(median(item.amount for item in ordered))
            if any(item.amount / center >= GatePolicy().exceptional_ratio for item in ordered):
                raise HistoryConflict("bootstrap contains an exceptional amount")
            identifier, created_at = uuid4(), datetime.now(UTC)
            evidence = tuple(
                LearningEvidence(
                    case_id, item[1].feedback_id, item[2].transaction_id, item[1].actor_id
                )
                for case_id, item in zip(ordered_ids, collected, strict=True)
            )
            profile = CustomerBehaviorProfile(
                customer_id=customer_id,
                currency=currency,
                as_of=ordered[-1].timestamp,
                observations=tuple(
                    ProfileObservation(
                        item.transaction_id, item.amount, item.timestamp, item.recipient_id
                    )
                    for item in ordered
                ),
                version=1,
                timezone=customer.timezone,
                admission_workflow_verified=True,
                admission_policy_version=POLICY_VERSION,
                learning_decision_id=identifier,
            )
            uow.profiles.save(profile, expected_version=0)
            return self._finish(
                uow,
                principal,
                key,
                request_hash,
                initial_tx.transaction_id,
                identifier,
                customer_id,
                currency,
                LearningKind.BOOTSTRAP,
                ProfileUpdateAction.ACCEPT,
                "TRUSTED_REVIEWED_BOOTSTRAP",
                None,
                1,
                created_at,
                evidence,
            )

    def retrieve(self, principal: Principal, decision_id: UUID) -> LearningDecision:
        _require_admin(principal)
        with self.uow_factory() as uow:
            decision = uow.learning.get(decision_id)
            if decision is None or not principal.can_read(decision.customer_id):
                raise NotFound("learning decision not found")
            return decision

    def _finish(
        self,
        uow: UnitOfWork,
        principal: Principal,
        key: str,
        request_hash: str,
        idempotency_transaction_id: UUID,
        identifier: UUID,
        customer_id: UUID,
        currency: str,
        kind: LearningKind,
        action: ProfileUpdateAction,
        reason: str,
        before: int | None,
        after: int | None,
        created_at: datetime,
        evidence: tuple[LearningEvidence, ...],
    ) -> SubmissionResult:
        response = _response(
            identifier,
            customer_id,
            currency,
            principal.principal_id,
            kind,
            action,
            reason,
            before,
            after,
            created_at,
            evidence,
        )
        decision = LearningDecision(
            identifier,
            customer_id,
            currency,
            principal.principal_id,
            kind,
            action,
            reason,
            POLICY_VERSION,
            before,
            after,
            created_at,
            response,
            evidence,
        )
        uow.learning.add(decision)
        correlation = uuid4()
        uow.audit.add(
            AuditEvent(
                uuid4(),
                principal.principal_id,
                "profile.learning." + kind.value.lower(),
                identifier,
                correlation,
                created_at,
                f"{action.value}: {reason}; independent reviewed evidence required.",
            )
        )
        event = (
            EventType.PROFILE_UPDATED
            if action == ProfileUpdateAction.ACCEPT
            else EventType.PROFILE_TRANSACTION_QUARANTINED
            if action == ProfileUpdateAction.QUARANTINE
            else EventType.PROFILE_TRANSACTION_REJECTED
        )
        uow.outbox.add(
            DomainEvent(
                uuid4(),
                event,
                customer_id,
                created_at,
                correlation,
                (
                    ("decision_id", str(identifier)),
                    ("action", action.value),
                    ("policy_version", POLICY_VERSION),
                ),
            )
        )
        uow.idempotency.add(
            IdempotencyRecord(
                principal.principal_id,
                key,
                request_hash,
                idempotency_transaction_id,
                response,
                201,
                created_at,
            )
        )
        uow.commit()
        return SubmissionResult(response, 201, False)
