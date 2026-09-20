from dataclasses import asdict
from uuid import UUID

from sqlalchemy import select

from backend.adapters.database.models import CaseRow, TransitionRow
from backend.adapters.database.repository_base import Repository
from backend.app.cases.entities import CaseState, CaseTransition, FraudCase
from backend.app.shared.errors import ConcurrentUpdate, HistoryConflict


class PostgresFraudCaseRepository(Repository):
    def get(self, case_id: UUID) -> FraudCase | None:
        row = self.session.get(CaseRow, case_id)
        if row is None:
            return None
        history = self.session.scalars(
            select(TransitionRow)
            .where(TransitionRow.case_id == case_id)
            .order_by(TransitionRow.sequence)
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

    def save(self, case: FraudCase) -> None:
        row = self.session.scalar(
            select(CaseRow).where(CaseRow.case_id == case.case_id).with_for_update()
        )
        if row is None:
            self.session.add(
                CaseRow(
                    case_id=case.case_id,
                    transaction_id=case.transaction_id,
                    assessment_id=case.assessment_id,
                    created_at=case.created_at,
                )
            )
            self.session.flush()
            previous_length = 0
        else:
            persisted = self.get(case.case_id)
            assert persisted is not None
            if (persisted.transaction_id, persisted.assessment_id, persisted.created_at) != (
                case.transaction_id,
                case.assessment_id,
                case.created_at,
            ):
                raise HistoryConflict("case identity is immutable")
            previous_length = len(persisted.history)
            if case.history[:previous_length] != persisted.history:
                raise ConcurrentUpdate("case history changed since it was read")
        for sequence, transition in enumerate(
            case.history[previous_length:], start=previous_length + 1
        ):
            self.session.add(
                TransitionRow(case_id=case.case_id, sequence=sequence, **asdict(transition))
            )
            self.session.flush()
