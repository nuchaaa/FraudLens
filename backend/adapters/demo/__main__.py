"""Preview, apply or inspect synthetic facts in disposable local PostgreSQL."""

import argparse
import json
import os
from collections import Counter
from functools import partial

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.adapters.database.base import create_database_engine
from backend.adapters.database.models import (
    EvaluationRow,
    ObservationRow,
    ProfileLearningDecisionRow,
    ProfileLearningEvidenceRow,
    ProfileRevisionRow,
    ProfileRow,
    TransactionRow,
)
from backend.adapters.database.uow import create_unit_of_work
from backend.adapters.demo.progress import _matches, evidence_report
from backend.adapters.demo.walkthrough import render_walkthrough
from backend.app.demo.scenarios import VERSION, DemoEvent, DemoPlan, build_plan, demo_id
from backend.app.demo.stages import (
    STAGES,
    fixture_bootstrap_trace_matches,
    predecessor,
    stage_events,
)
from backend.app.shared.security import Principal, Role
from backend.app.transaction.service import TransactionService


class StageConflictError(ValueError):
    """A stable fixture ID already identifies different stored facts."""


class StagePrerequisiteError(ValueError):
    """The disposable demo lacks evidence needed before a new stage."""


def require_disposable(engine: Engine) -> None:
    """The local seeder must never accept a production or TCP database URL."""
    host = engine.url.query.get("host")
    if (
        not (engine.url.database or "").endswith("_test")
        or not isinstance(host, str)
        or not host.startswith("/")
        or os.getenv("FRAUDLENS_ENVIRONMENT", "development") == "production"
    ):
        raise ValueError("demo seeding requires a local Unix-socket *_test database")


def _apply_events(engine: Engine, plan: DemoPlan, events: tuple[DemoEvent, ...]) -> tuple[int, int]:
    factory = partial(create_unit_of_work, engine)
    service = TransactionService(factory)
    actor = Principal(demo_id("actor/local-seeder"), frozenset({Role.ADMIN}))
    key_prefix = plan.sha256()[:20]
    for customer_id in sorted({event.transaction.customer_id for event in events}):
        with factory() as uow:
            existing = uow.customers.get(customer_id)
        if existing is None:
            service.enroll_customer(actor, customer_id, "Asia/Almaty")
        elif existing.timezone != "Asia/Almaty":
            raise ValueError("demo customer ID collides with an incompatible customer")
    created = replayed = 0
    for event in events:
        result = service.submit(
            actor,
            f"{key_prefix}:{event.transaction.transaction_id}",
            event.transaction,
        )
        if result.replayed:
            replayed += 1
        else:
            created += 1
    return created, replayed


def apply_plan(engine: Engine, plan: DemoPlan) -> tuple[int, int]:
    """Use existing domain services, preserving audit, outbox and idempotency."""
    require_disposable(engine)
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(17572, 16)"))
        return _apply_events(engine, plan, plan.events)


def _require_stage(
    engine: Engine, plan: DemoPlan, stage: str
) -> tuple[tuple[DemoEvent, ...], bool]:
    events = stage_events(plan, stage)
    with Session(engine, autobegin=False) as session, session.begin():
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        stored = [session.get(TransactionRow, event.transaction.transaction_id) for event in events]
        if any(
            row is not None and not _matches(row, event)
            for row, event in zip(stored, events, strict=True)
        ):
            raise StageConflictError("demo stage conflicts with stored transaction facts")
        if all(row is not None for row in stored):
            return events, True  # Exact replay does not assert original stage chronology.
        if stage == "BASELINE":
            missing_owners = {
                event.transaction.customer_id
                for row, event in zip(stored, events, strict=True)
                if row is None
            }
            if any(session.get(ProfileRow, (owner, "KZT")) is not None for owner in missing_owners):
                raise StagePrerequisiteError(
                    "cannot backfill baseline after a customer profile exists"
                )
            if any(
                session.get(TransactionRow, event.transaction.transaction_id) is not None
                for event in plan.events
                if event.story != "unreviewed normal-looking history"
                and event.transaction.customer_id in missing_owners
            ):
                raise StagePrerequisiteError(
                    "cannot backfill baseline after a candidate was inserted"
                )
            return events, False
        event = events[0]
        customer_id = event.transaction.customer_id
        baseline = tuple(
            item
            for item in stage_events(plan, "BASELINE")
            if item.transaction.customer_id == customer_id
        )
        if any(
            row is None or not _matches(row, item)
            for item in baseline
            for row in (session.get(TransactionRow, item.transaction.transaction_id),)
        ):
            raise StagePrerequisiteError("stage requires matching earlier customer baseline facts")
        if any(
            session.get(TransactionRow, item.transaction.transaction_id) is not None
            for item in plan.events
            if item.transaction.customer_id == customer_id
            and item.transaction.timestamp > event.transaction.timestamp
        ):
            raise StagePrerequisiteError(
                "cannot insert an earlier stage after later customer facts"
            )
        if stage != "A":
            profile = session.get(ProfileRow, (customer_id, "KZT"))
            if (
                profile is None
                or not profile.admission_workflow_verified
                or profile.as_of >= event.transaction.timestamp
            ):
                raise StagePrerequisiteError("stage requires a verified prior KZT profile")
            initial = session.get(ProfileRevisionRow, (customer_id, "KZT", 1))
            bootstrap_decision = (
                session.get(ProfileLearningDecisionRow, initial.learning_decision_id)
                if initial is not None and initial.learning_decision_id is not None
                else None
            )
            baseline_ids = frozenset(item.transaction.transaction_id for item in baseline)
            if (
                initial is None
                or not initial.admission_workflow_verified
                or bootstrap_decision is None
                or bootstrap_decision.customer_id != customer_id
                or bootstrap_decision.currency != "KZT"
                or bootstrap_decision.kind != "BOOTSTRAP"
                or bootstrap_decision.action != "ACCEPT"
                or bootstrap_decision.profile_version_before is not None
                or bootstrap_decision.profile_version_after != 1
                or not fixture_bootstrap_trace_matches(
                    baseline_ids,
                    session.scalars(
                        select(ObservationRow.transaction_id).where(
                            ObservationRow.customer_id == customer_id,
                            ObservationRow.currency == "KZT",
                            ObservationRow.admitted_version == 1,
                            ObservationRow.transaction_id.in_(baseline_ids),
                        )
                    ).all(),
                    session.execute(
                        select(
                            ProfileLearningEvidenceRow.transaction_id,
                            ProfileLearningEvidenceRow.reviewer_id,
                        ).where(
                            ProfileLearningEvidenceRow.decision_id
                            == bootstrap_decision.decision_id,
                            ProfileLearningEvidenceRow.transaction_id.in_(baseline_ids),
                        )
                    )
                    .tuples()
                    .all(),
                )
            ):
                raise StagePrerequisiteError("stage requires reviewed fixture baseline provenance")
        previous = predecessor(stage)
        if previous is not None:
            prior = stage_events(plan, previous)[0]
            row = session.get(TransactionRow, prior.transaction.transaction_id)
            if row is None or not _matches(row, prior):
                raise StagePrerequisiteError("stage requires its matching prior candidate")
            evaluated = session.scalar(
                select(EvaluationRow.evaluation_id)
                .where(EvaluationRow.transaction_id == prior.transaction.transaction_id)
                .limit(1)
            )
            if evaluated is None:
                raise StagePrerequisiteError("stage requires a retained prior evaluation")
            if stage == "C" or stage.startswith("D"):
                learning_query = (
                    select(ProfileLearningDecisionRow)
                    .join(
                        ProfileLearningEvidenceRow,
                        ProfileLearningDecisionRow.decision_id
                        == ProfileLearningEvidenceRow.decision_id,
                    )
                    .where(
                        ProfileLearningEvidenceRow.transaction_id
                        == prior.transaction.transaction_id,
                        ProfileLearningDecisionRow.kind == "CASE_UPDATE",
                    )
                )
                if stage == "C":
                    learning_query = learning_query.where(
                        ProfileLearningDecisionRow.action == "QUARANTINE",
                        ProfileLearningDecisionRow.reason == "EXCEPTIONAL_LEGITIMATE_AMOUNT",
                        ProfileLearningDecisionRow.profile_version_before
                        == ProfileLearningDecisionRow.profile_version_after,
                    )
                else:
                    learning_query = learning_query.where(
                        ProfileLearningDecisionRow.action == "ACCEPT"
                    )
                decision = session.scalar(learning_query.limit(1))
                if decision is None and stage == "C":
                    raise StagePrerequisiteError(
                        "follow-up stage requires B's exceptional quarantine decision"
                    )
                if decision is None:
                    raise StagePrerequisiteError(
                        "gradual stage requires a separately authorized prior admission"
                    )
    return events, False


def check_stage(engine: Engine, plan: DemoPlan, stage: str) -> dict[str, object]:
    """Preview one stage under the same read-only guard used immediately before writes."""
    require_disposable(engine)
    try:
        events, replayable = _require_stage(engine, plan, stage)
    except StageConflictError as exc:
        return {"stage": stage, "state": "CONFLICT", "reason": str(exc), "read_only": True}
    except StagePrerequisiteError as exc:
        return {"stage": stage, "state": "BLOCKED", "reason": str(exc), "read_only": True}
    return {
        "stage": stage,
        "state": "REPLAYABLE" if replayable else "READY",
        "transaction_count": len(events),
        "read_only": True,
    }


def apply_stage(engine: Engine, plan: DemoPlan, stage: str) -> tuple[int, int]:
    """Insert one stage only after stored facts and independent workflow gates."""
    require_disposable(engine)
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(17572, 16)"))
        events, _ = _require_stage(engine, plan, stage)
        return _apply_events(engine, plan, events)


def summary(plan: DemoPlan) -> dict[str, object]:
    return {
        "version": VERSION,
        "manifest_sha256": plan.sha256(),
        "synthetic_only": True,
        "production_eligible": False,
        "customers": [str(identifier) for identifier in plan.customers],
        "transactions": len(plan.events),
        "scenario_counts": dict(sorted(Counter(event.scenario for event in plan.events).items())),
        "fixture_actor_id": str(demo_id("actor/local-seeder")),
        "note": (
            "The fixture creates no profile admissions, analyst verdicts, "
            "risk evaluations or measured outcomes."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--manifest", action="store_true", help="print all synthetic facts")
    action.add_argument("--apply", action="store_true", help="write to TEST_DATABASE_URL only")
    action.add_argument(
        "--apply-stage",
        choices=STAGES,
        metavar="STAGE",
        help="seed BASELINE, A, B, C, D1-D5 or E1-E6 with prerequisites",
    )
    action.add_argument(
        "--check-stage",
        choices=STAGES,
        metavar="STAGE",
        help="read-only stage readiness preview; rechecked on apply",
    )
    action.add_argument("--progress", action="store_true", help="read stored demo evidence")
    action.add_argument("--walkthrough", action="store_true", help="print a read-only story guide")
    args = parser.parse_args()
    plan = build_plan()
    if args.apply or args.apply_stage or args.check_stage or args.progress or args.walkthrough:
        url = os.getenv("TEST_DATABASE_URL")
        if not url:
            parser.error("TEST_DATABASE_URL is required for database demo actions")
        engine = create_database_engine(url)
        try:
            require_disposable(engine)
            if args.apply:
                created, replayed = apply_plan(engine, plan)
                report = summary(plan) | {"created": created, "replayed": replayed}
            elif args.apply_stage:
                created, replayed = apply_stage(engine, plan, args.apply_stage)
                report = summary(plan) | {
                    "stage": args.apply_stage,
                    "created": created,
                    "replayed": replayed,
                    "stage_events": len(stage_events(plan, args.apply_stage)),
                }
            elif args.check_stage:
                report = check_stage(engine, plan, args.check_stage)
            elif args.walkthrough:
                print(render_walkthrough(plan, evidence_report(engine, plan)), end="")
                return
            else:
                report = evidence_report(engine, plan)
        finally:
            engine.dispose()
    else:
        report = plan.document() if args.manifest else summary(plan)
    print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
