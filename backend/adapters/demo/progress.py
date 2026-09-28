"""Read-only evidence inventory for the disposable five-story fixture."""

import json
from collections import Counter

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.adapters.database.models import (
    EvaluationCaseRow,
    EvaluationFeedbackRow,
    EvaluationRow,
    EvaluationTransitionRow,
    ObservationRow,
    ProfileLearningDecisionRow,
    ProfileLearningEvidenceRow,
    ProfileRevisionRow,
    ProfileRow,
    TransactionRow,
)
from backend.adapters.database.profiles import PostgresCustomerProfileRepository
from backend.app.demo.scenarios import DemoEvent, DemoPlan


def _matches(row: TransactionRow, event: DemoEvent) -> bool:
    expected = event.transaction
    return (
        row.customer_id == expected.customer_id
        and row.recipient_id == expected.recipient_id
        and row.amount == expected.amount
        and row.currency == expected.currency
        and row.timestamp == expected.timestamp
        and row.channel == expected.channel.value
        and row.device_id == expected.device_id
        and row.status == expected.status.value
    )


def evidence_report(engine: Engine, plan: DemoPlan) -> dict[str, object]:
    """Inventory persisted evidence; narrative story text is never a verdict."""
    events: list[dict[str, object]] = []
    profiles: list[dict[str, object]] = []
    # A single read-only transaction gives one consistent view of the fixture.
    with Session(engine, autobegin=False) as session, session.begin():
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        fixture_ids = {event.transaction.transaction_id for event in plan.events}
        profile_repository = PostgresCustomerProfileRepository(session)
        for customer_id in plan.customers:
            profile = session.get(ProfileRow, (customer_id, "KZT"))
            revision_rows = session.scalars(
                select(ProfileRevisionRow)
                .where(
                    ProfileRevisionRow.customer_id == customer_id,
                    ProfileRevisionRow.currency == "KZT",
                )
                .order_by(ProfileRevisionRow.version)
            ).all()
            revision_reports: list[dict[str, object]] = []
            for revision in revision_rows:
                snapshot = profile_repository.get_revision(
                    customer_id, "KZT", version=revision.version
                )
                assert snapshot is not None
                summary = snapshot.long_term
                revision_reports.append(
                    {
                        "version": snapshot.version,
                        "as_of": snapshot.as_of.isoformat(),
                        "admission_workflow_verified": snapshot.admission_workflow_verified,
                        "learning_decision_id": (
                            str(snapshot.learning_decision_id)
                            if snapshot.learning_decision_id
                            else None
                        ),
                        "long_term_count": summary.count if summary else 0,
                        "long_term_median": str(summary.median) if summary else None,
                        "admitted_fixture_transaction_ids": sorted(
                            str(item.transaction_id)
                            for item in snapshot.observations
                            if item.transaction_id in fixture_ids
                        ),
                    }
                )
            observations = session.scalars(
                select(ObservationRow).where(
                    ObservationRow.customer_id == customer_id,
                    ObservationRow.currency == "KZT",
                )
            ).all()
            profiles.append(
                {
                    "customer_id": str(customer_id),
                    "current_version": profile.version if profile else None,
                    "admission_workflow_verified": (
                        profile.admission_workflow_verified if profile else False
                    ),
                    "revisions": revision_reports,
                    "admitted_fixture_transaction_ids": sorted(
                        str(item.transaction_id)
                        for item in observations
                        if item.transaction_id in fixture_ids
                    ),
                }
            )
        for event in plan.events:
            tx = event.transaction
            row = session.get(TransactionRow, tx.transaction_id)
            state = "ABSENT" if row is None else "MATCH" if _matches(row, event) else "CONFLICT"
            if state != "MATCH":
                events.append(
                    {
                        "scenario": event.scenario,
                        "transaction_id": str(tx.transaction_id),
                        "customer_id": str(tx.customer_id),
                        "timestamp": tx.timestamp.isoformat(),
                        "fixture_fact": state,
                        "prior_profile_revisions": [],
                        "evaluations": [],
                    }
                )
                continue
            evaluations = session.scalars(
                select(EvaluationRow)
                .where(EvaluationRow.transaction_id == tx.transaction_id)
                .order_by(EvaluationRow.created_at, EvaluationRow.evaluation_id)
            ).all()
            recorded: list[dict[str, object]] = []
            for evaluation in evaluations:
                cases = session.scalars(
                    select(EvaluationCaseRow).where(
                        EvaluationCaseRow.assessment_id == evaluation.evaluation_id
                    )
                ).all()
                case_reports: list[dict[str, object]] = []
                for case in cases:
                    transition = session.scalar(
                        select(EvaluationTransitionRow)
                        .where(EvaluationTransitionRow.case_id == case.case_id)
                        .order_by(EvaluationTransitionRow.sequence.desc())
                        .limit(1)
                    )
                    feedback = session.scalars(
                        select(EvaluationFeedbackRow)
                        .where(EvaluationFeedbackRow.case_id == case.case_id)
                        .order_by(EvaluationFeedbackRow.sequence)
                    ).all()
                    learning = session.scalars(
                        select(ProfileLearningDecisionRow)
                        .join(
                            ProfileLearningEvidenceRow,
                            ProfileLearningDecisionRow.decision_id
                            == ProfileLearningEvidenceRow.decision_id,
                        )
                        .where(ProfileLearningEvidenceRow.case_id == case.case_id)
                    ).all()
                    case_reports.append(
                        {
                            "case_id": str(case.case_id),
                            "state": transition.target if transition else "OPEN",
                            "feedback": [
                                {"feedback_id": str(item.feedback_id), "verdict": item.verdict}
                                for item in feedback
                            ],
                            "learning": [
                                {
                                    "decision_id": str(item.decision_id),
                                    "action": item.action,
                                    "reason": item.reason,
                                    "profile_version_before": item.profile_version_before,
                                    "profile_version_after": item.profile_version_after,
                                }
                                for item in learning
                            ],
                        }
                    )
                risk = json.loads(evaluation.response_json).get("risk", {})
                recorded.append(
                    {
                        "evaluation_id": str(evaluation.evaluation_id),
                        "risk_status": risk.get("status"),
                        "captured_profile_version": risk.get("profile_version"),
                        "cases": case_reports,
                    }
                )
            revisions = session.scalars(
                select(ProfileRevisionRow)
                .where(
                    ProfileRevisionRow.customer_id == tx.customer_id,
                    ProfileRevisionRow.currency == tx.currency,
                    ProfileRevisionRow.as_of < tx.timestamp,
                    ProfileRevisionRow.admission_workflow_verified.is_(True),
                )
                .order_by(ProfileRevisionRow.version)
            ).all()
            events.append(
                {
                    "scenario": event.scenario,
                    "transaction_id": str(tx.transaction_id),
                    "customer_id": str(tx.customer_id),
                    "timestamp": tx.timestamp.isoformat(),
                    "fixture_fact": state,
                    "prior_profile_revisions": [item.version for item in revisions],
                    "evaluations": recorded,
                }
            )
    return {
        "version": "demo-evidence-v1",
        "manifest_sha256": plan.sha256(),
        "synthetic_only": True,
        "production_eligible": False,
        "read_only": True,
        "fixture_fact_counts": dict(
            sorted(Counter(str(item["fixture_fact"]) for item in events).items())
        ),
        "profiles": profiles,
        "events": events,
        "limits": [
            "Story descriptions are authored intent, never analyst verdicts.",
            "Prior profile revisions fit event time but do not prove historical availability.",
            "Recorded feedback and learning are shown separately; none is inferred from intake.",
            "All fixture facts were inserted at demo time, not their event timestamps.",
        ],
    }
