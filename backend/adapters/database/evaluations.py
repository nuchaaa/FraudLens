from dataclasses import asdict
from uuid import UUID

from sqlalchemy import select

from backend.adapters.database.models import (
    EvaluationCaseRow,
    EvaluationFeedbackRow,
    EvaluationRow,
    EvaluationTransitionRow,
)
from backend.adapters.database.repository_base import Repository
from backend.app.cases.entities import CaseState, CaseTransition, FraudCase
from backend.app.evaluation.contracts import EvaluationRecord, ReviewFeedback
from backend.app.feedback.entities import AnalystVerdict
from backend.app.shared.errors import ConcurrentUpdate, HistoryConflict


class PostgresEvaluationRepository(Repository):
    def add(self, record: EvaluationRecord) -> None:
        self.session.add(EvaluationRow(**asdict(record)))
        self.session.flush()

    def get(self, evaluation_id: UUID) -> EvaluationRecord | None:
        row = self.session.get(EvaluationRow, evaluation_id)
        return (
            EvaluationRecord(
                row.evaluation_id,
                row.transaction_id,
                row.customer_id,
                row.currency,
                row.actor_id,
                row.created_at,
                row.response_json,
            )
            if row
            else None
        )


class PostgresEvaluationReviewRepository(Repository):
    def get(self, case_id: UUID, *, lock: bool = False) -> FraudCase | None:
        query = select(EvaluationCaseRow).where(EvaluationCaseRow.case_id == case_id)
        if lock:
            query = query.with_for_update()
        row = self.session.scalar(query)
        if row is None:
            return None
        history = self.session.scalars(
            select(EvaluationTransitionRow)
            .where(EvaluationTransitionRow.case_id == case_id)
            .order_by(EvaluationTransitionRow.sequence)
        ).all()
        return FraudCase(
            row.case_id,
            row.transaction_id,
            row.assessment_id,
            row.created_at,
            tuple(
                CaseTransition(CaseState(t.previous), CaseState(t.target), t.actor_id, t.timestamp)
                for t in history
            ),
        )

    def find(self, evaluation_id: UUID) -> FraudCase | None:
        row = self.session.scalar(
            select(EvaluationCaseRow).where(EvaluationCaseRow.assessment_id == evaluation_id)
        )
        return self.get(row.case_id) if row else None

    def save(self, case: FraudCase) -> None:
        stored = self.get(case.case_id, lock=True)
        if stored is None:
            self.session.add(
                EvaluationCaseRow(
                    case_id=case.case_id,
                    transaction_id=case.transaction_id,
                    assessment_id=case.assessment_id,
                    created_at=case.created_at,
                )
            )
            self.session.flush()
            length = 0
        else:
            if (case.transaction_id, case.assessment_id, case.created_at) != (
                stored.transaction_id,
                stored.assessment_id,
                stored.created_at,
            ):
                raise HistoryConflict("case identity is immutable")
            length = len(stored.history)
            if case.history[:length] != stored.history:
                raise ConcurrentUpdate("case history changed")
        for sequence, transition in enumerate(case.history[length:], start=length + 1):
            self.session.add(
                EvaluationTransitionRow(
                    case_id=case.case_id, sequence=sequence, **asdict(transition)
                )
            )
            self.session.flush()

    def feedback(self, case_id: UUID) -> tuple[ReviewFeedback, ...]:
        rows = self.session.scalars(
            select(EvaluationFeedbackRow)
            .where(EvaluationFeedbackRow.case_id == case_id)
            .order_by(EvaluationFeedbackRow.sequence)
        ).all()
        return tuple(
            ReviewFeedback(
                r.feedback_id,
                r.case_id,
                r.actor_id,
                AnalystVerdict(r.verdict),
                r.timestamp,
                r.comment,
                r.sequence,
            )
            for r in rows
        )

    def add_feedback(self, feedback: ReviewFeedback) -> None:
        self.session.add(EvaluationFeedbackRow(**asdict(feedback)))
        self.session.flush()
