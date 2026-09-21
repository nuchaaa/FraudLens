"""Authorized experimental evaluation and case review, with exact durable replay."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.app.audit.entities import AuditEvent
from backend.app.cases.entities import CaseState, FraudCase, InvalidCaseTransition
from backend.app.evaluation.contracts import EvaluationEngine, EvaluationRecord, ReviewFeedback
from backend.app.features.service import FeatureService
from backend.app.feedback.entities import AnalystVerdict
from backend.app.risk.service import RiskPolicy, Strategy
from backend.app.shared.errors import ConcurrentUpdate, HistoryConflict
from backend.app.shared.events import DomainEvent, EventType
from backend.app.shared.ports import UnitOfWork
from backend.app.shared.security import Forbidden, NotFound, Principal, Role
from backend.app.transaction.idempotency import IdempotencyRecord
from backend.app.transaction.service import (
    SubmissionResult,
    UnitOfWorkFactory,
    validate_idempotency_key,
)


def digest(operation: str, values: object) -> str:
    body = json.dumps(values, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256((operation + ":v1\n" + body).encode()).hexdigest()


def finish(
    uow: UnitOfWork,
    principal: Principal,
    key: str,
    request_hash: str,
    transaction_id: UUID,
    entity_id: UUID,
    response: str,
    action: str,
    event: EventType,
    *,
    status: int = 201,
) -> SubmissionResult:
    now, correlation = datetime.now(UTC), uuid4()
    uow.audit.add(
        AuditEvent(
            uuid4(),
            principal.principal_id,
            action,
            entity_id,
            correlation,
            now,
            "Experimental review only; no operational action or profile admission.",
        )
    )
    uow.outbox.add(
        DomainEvent(
            uuid4(),
            event,
            entity_id,
            now,
            correlation,
            (("transaction_id", str(transaction_id)), ("experimental", "true")),
        )
    )
    uow.idempotency.add(
        IdempotencyRecord(
            principal.principal_id, key, request_hash, transaction_id, response, status, now
        )
    )
    uow.commit()
    return SubmissionResult(response, status, False)


class EvaluationService:
    def __init__(self, uow_factory: UnitOfWorkFactory, engine: EvaluationEngine) -> None:
        self.uow_factory, self.engine = uow_factory, engine

    def submit(
        self,
        principal: Principal,
        key: str,
        transaction_id: UUID,
        *,
        profile_version: int | None,
        strategy: Strategy,
        manifest_sha256: str | None,
    ) -> SubmissionResult:
        validate_idempotency_key(key)
        request_hash = digest(
            "experimental-evaluate",
            {
                "transaction_id": str(transaction_id),
                "profile_version": profile_version,
                "policy_sha256": RiskPolicy(strategy).fingerprint,
                "manifest_sha256": manifest_sha256,
            },
        )
        with self.uow_factory() as uow:
            tx = uow.transactions.get(transaction_id)
            if tx is None or not principal.can_read(tx.customer_id):
                raise NotFound("transaction not found")
            if not principal.can_submit(tx.customer_id):
                raise Forbidden("evaluation requires a scoped service or admin role")
            prior = uow.idempotency.acquire(principal.principal_id, key, request_hash)
            if prior:
                return SubmissionResult(prior.response_json, prior.status_code, True)
            context = FeatureService(self.uow_factory).capture_in(
                uow, principal, transaction_id, profile_version=profile_version
            )
            payload = json.loads(self.engine.render(context, strategy, manifest_sha256))
            identifier, created = uuid4(), datetime.now(UTC)
            payload.update(
                schema_version="experimental-evaluation-v1",
                evaluation_id=str(identifier),
                transaction_id=str(tx.transaction_id),
                customer_id=str(tx.customer_id),
                currency=tx.currency,
                actor_id=str(principal.principal_id),
                created_at=created.isoformat(),
            )
            response = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
            record = EvaluationRecord(
                identifier,
                tx.transaction_id,
                tx.customer_id,
                tx.currency,
                principal.principal_id,
                created,
                response,
            )
            uow.evaluations.add(record)
            return finish(
                uow,
                principal,
                key,
                request_hash,
                tx.transaction_id,
                identifier,
                response,
                "experimental.evaluation.created",
                EventType.RISK_EVALUATED,
            )

    def retrieve(self, principal: Principal, evaluation_id: UUID) -> EvaluationRecord:
        with self.uow_factory() as uow:
            return authorized_evaluation(uow, principal, evaluation_id)


def authorized_evaluation(
    uow: UnitOfWork, principal: Principal, evaluation_id: UUID
) -> EvaluationRecord:
    record = uow.evaluations.get(evaluation_id)
    if record is None or not principal.can_read(record.customer_id):
        raise NotFound("evaluation not found")
    return record


def require_reviewer(principal: Principal) -> None:
    if not principal.roles & {Role.ADMIN, Role.ANALYST}:
        raise Forbidden("case review requires analyst or admin role")


def review_document(uow: UnitOfWork, case: FraudCase) -> str:
    feedback = uow.reviews.feedback(case.case_id)
    return json.dumps(
        {
            "case_id": str(case.case_id),
            "evaluation_id": str(case.assessment_id),
            "transaction_id": str(case.transaction_id),
            "created_at": case.created_at.isoformat(),
            "state": case.state.value,
            "version": len(case.history) + len(feedback),
            "history": [
                {
                    "previous": t.previous.value,
                    "target": t.target.value,
                    "actor_id": str(t.actor_id),
                    "timestamp": t.timestamp.isoformat(),
                }
                for t in case.history
            ],
            "feedback": [
                {
                    "feedback_id": str(f.feedback_id),
                    "actor_id": str(f.actor_id),
                    "verdict": f.verdict.value,
                    "timestamp": f.timestamp.isoformat(),
                    "comment": f.comment,
                    "sequence": f.sequence,
                }
                for f in feedback
            ],
            "experimental": True,
            "operational_action_executed": False,
            "admission_workflow_verified": False,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class ReviewService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self.uow_factory = uow_factory

    def create(self, principal: Principal, key: str, evaluation_id: UUID) -> SubmissionResult:
        require_reviewer(principal)
        validate_idempotency_key(key)
        request_hash = digest("experimental-case", str(evaluation_id))
        with self.uow_factory() as uow:
            evaluation = authorized_evaluation(uow, principal, evaluation_id)
            prior = uow.idempotency.acquire(principal.principal_id, key, request_hash)
            if prior:
                return SubmissionResult(prior.response_json, prior.status_code, True)
            if uow.reviews.find(evaluation_id):
                raise HistoryConflict("evaluation already has a case")
            case = FraudCase(uuid4(), evaluation.transaction_id, evaluation_id, datetime.now(UTC))
            uow.reviews.save(case)
            return finish(
                uow,
                principal,
                key,
                request_hash,
                case.transaction_id,
                case.case_id,
                review_document(uow, case),
                "experimental.case.created",
                EventType.FRAUD_CASE_CREATED,
            )

    def retrieve(self, principal: Principal, case_id: UUID) -> str:
        with self.uow_factory() as uow:
            case = uow.reviews.get(case_id, lock=True)
            if case is None:
                raise NotFound("case not found")
            authorized_evaluation(uow, principal, case.assessment_id)
            return review_document(uow, case)

    def change(
        self,
        principal: Principal,
        key: str,
        case_id: UUID,
        *,
        expected_version: int,
        action: str,
        verdict: AnalystVerdict | None = None,
        comment: str | None = None,
    ) -> SubmissionResult:
        require_reviewer(principal)
        validate_idempotency_key(key)
        request_hash = digest(
            "experimental-review",
            {
                "case_id": str(case_id),
                "expected_version": expected_version,
                "action": action,
                "verdict": verdict,
                "comment": comment,
            },
        )
        with self.uow_factory() as uow:
            # Read-only authorization first; advisory lock before the row lock and any writes.
            case = uow.reviews.get(case_id)
            if case is None:
                raise NotFound("case not found")
            authorized_evaluation(uow, principal, case.assessment_id)
            prior = uow.idempotency.acquire(principal.principal_id, key, request_hash)
            if prior:
                return SubmissionResult(prior.response_json, prior.status_code, True)
            case = uow.reviews.get(case_id, lock=True)
            assert case is not None
            feedback = uow.reviews.feedback(case_id)
            if expected_version != len(case.history) + len(feedback):
                raise ConcurrentUpdate("case version changed")
            now = datetime.now(UTC)
            if action == "start_review":
                case = case.transition(CaseState.UNDER_REVIEW, principal.principal_id, now)
            elif action == "close":
                case = case.transition(CaseState.CLOSED, principal.principal_id, now)
            elif action == "feedback":
                if case.state != CaseState.UNDER_REVIEW or verdict is None or comment is None:
                    raise InvalidCaseTransition(
                        "feedback requires an under-review case and verdict/comment"
                    )
                if verdict != AnalystVerdict.NEEDS_INVESTIGATION:
                    case = case.transition(CaseState(verdict.value), principal.principal_id, now)
            else:
                raise ValueError("unknown review action")
            uow.reviews.save(case)
            if action == "feedback":
                assert verdict is not None and comment is not None
                uow.reviews.add_feedback(
                    ReviewFeedback(
                        uuid4(),
                        case_id,
                        principal.principal_id,
                        verdict,
                        now,
                        comment,
                        len(feedback) + 1,
                    )
                )
            return finish(
                uow,
                principal,
                key,
                request_hash,
                case.transaction_id,
                case_id,
                review_document(uow, case),
                "experimental.case." + action,
                EventType.ANALYST_DECISION_MADE
                if action == "feedback"
                else EventType.CASE_REVIEW_CHANGED,
                status=200,
            )
