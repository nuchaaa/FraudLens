import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, false, func, or_, select, true
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from backend.adapters.database.models import (
    EvaluationCaseRow,
    EvaluationFeedbackRow,
    EvaluationRow,
    EvaluationTransitionRow,
    TransactionRow,
)
from backend.adapters.database.repository_base import Repository
from backend.adapters.database.transactions import transaction_from_row
from backend.app.cases.entities import CaseState
from backend.app.console.contracts import (
    ConsoleSummary,
    WorklistCursor,
    WorklistItem,
    WorklistPage,
)


def _scope(column: Any, customer_ids: frozenset[UUID] | None) -> ColumnElement[bool]:
    if customer_ids is None:
        return true()
    return cast(ColumnElement[bool], column.in_(customer_ids)) if customer_ids else false()


def _latest_evaluations() -> Subquery:
    ranked = select(
        EvaluationRow.evaluation_id,
        EvaluationRow.transaction_id,
        EvaluationRow.customer_id,
        EvaluationRow.created_at,
        EvaluationRow.response_json,
        func.row_number()
        .over(
            partition_by=EvaluationRow.transaction_id,
            order_by=(EvaluationRow.created_at.desc(), EvaluationRow.evaluation_id.desc()),
        )
        .label("position"),
    ).subquery()
    return select(ranked).where(ranked.c.position == 1).subquery()


class PostgresConsoleRepository(Repository):
    def worklist(
        self,
        customer_ids: frozenset[UUID] | None,
        *,
        limit: int,
        cursor: WorklistCursor | None,
    ) -> WorklistPage:
        query = select(TransactionRow).where(_scope(TransactionRow.customer_id, customer_ids))
        if cursor is not None:
            query = query.where(
                or_(
                    TransactionRow.timestamp < cursor.timestamp,
                    and_(
                        TransactionRow.timestamp == cursor.timestamp,
                        TransactionRow.transaction_id < cursor.transaction_id,
                    ),
                )
            )
        rows = self.session.scalars(
            query.order_by(
                TransactionRow.timestamp.desc(), TransactionRow.transaction_id.desc()
            ).limit(limit + 1)
        ).all()
        visible = rows[:limit]
        transaction_ids = [row.transaction_id for row in visible]
        evaluations = {}
        if transaction_ids:
            records = self.session.scalars(
                select(EvaluationRow)
                .where(EvaluationRow.transaction_id.in_(transaction_ids))
                .distinct(EvaluationRow.transaction_id)
                .order_by(
                    EvaluationRow.transaction_id,
                    EvaluationRow.created_at.desc(),
                    EvaluationRow.evaluation_id.desc(),
                )
            ).all()
            evaluations = {record.transaction_id: record for record in records}
        evaluation_ids = [record.evaluation_id for record in evaluations.values()]
        cases = {}
        states: dict[UUID, CaseState] = {}
        if evaluation_ids:
            case_rows = self.session.scalars(
                select(EvaluationCaseRow).where(EvaluationCaseRow.assessment_id.in_(evaluation_ids))
            ).all()
            cases = {row.assessment_id: row for row in case_rows}
            case_ids = [row.case_id for row in case_rows]
            transitions = self.session.execute(
                select(EvaluationTransitionRow.case_id, EvaluationTransitionRow.target)
                .where(EvaluationTransitionRow.case_id.in_(case_ids))
                .distinct(EvaluationTransitionRow.case_id)
                .order_by(
                    EvaluationTransitionRow.case_id,
                    EvaluationTransitionRow.sequence.desc(),
                )
            ).all()
            states = {case_id: CaseState(target) for case_id, target in transitions}
        items = []
        for row in visible:
            evaluation = evaluations.get(row.transaction_id)
            document = json.loads(evaluation.response_json) if evaluation else None
            risk = document["risk"] if document else None
            policy = risk["policy"] if risk else None
            linked_case = cases.get(evaluation.evaluation_id) if evaluation else None
            items.append(
                WorklistItem(
                    transaction_from_row(row),
                    evaluation.evaluation_id if evaluation else None,
                    evaluation.created_at if evaluation else None,
                    risk["status"] if risk else None,
                    policy["strategy"] if policy else None,
                    risk["score"] if risk else None,
                    risk["level"] if risk else None,
                    risk["suggested_action"] if risk else None,
                    linked_case.case_id if linked_case else None,
                    states.get(linked_case.case_id, CaseState.OPEN) if linked_case else None,
                )
            )
        next_cursor = None
        if len(rows) > limit:
            last = visible[-1]
            next_cursor = WorklistCursor(last.timestamp, last.transaction_id)
        return WorklistPage(tuple(items), next_cursor)

    def summary(self, customer_ids: frozenset[UUID] | None, *, as_of: datetime) -> ConsoleSummary:
        start = as_of.replace(hour=0, minute=0, second=0, microsecond=0)
        tx_scope = _scope(TransactionRow.customer_id, customer_ids)
        transactions, today = self.session.execute(
            select(
                func.count(),
                func.count().filter(
                    TransactionRow.timestamp >= start,
                    TransactionRow.timestamp < start + timedelta(days=1),
                    TransactionRow.timestamp <= as_of,
                ),
            ).where(tx_scope)
        ).one()

        latest = _latest_evaluations()
        evaluation_scope = _scope(latest.c.customer_id, customer_ids)
        risk = sql_cast(latest.c.response_json, JSONB)["risk"]
        level = risk["level"].astext
        high = level.in_(("HIGH", "CRITICAL"))
        evaluated, high_count, suspicious = self.session.execute(
            select(
                func.count(),
                func.count().filter(high),
                func.coalesce(func.sum(TransactionRow.amount).filter(high), 0),
            )
            .select_from(latest)
            .join(TransactionRow, TransactionRow.transaction_id == latest.c.transaction_id)
            .where(evaluation_scope)
        ).one()

        latest_state = (
            select(EvaluationTransitionRow.target)
            .where(EvaluationTransitionRow.case_id == EvaluationCaseRow.case_id)
            .order_by(EvaluationTransitionRow.sequence.desc())
            .limit(1)
            .scalar_subquery()
        )
        latest_verdict = (
            select(EvaluationFeedbackRow.verdict)
            .where(EvaluationFeedbackRow.case_id == EvaluationCaseRow.case_id)
            .order_by(EvaluationFeedbackRow.sequence.desc())
            .limit(1)
            .scalar_subquery()
        )
        case_scope = _scope(EvaluationRow.customer_id, customer_ids)
        awaiting, confirmed = self.session.execute(
            select(
                func.count().filter(
                    func.coalesce(latest_state, CaseState.OPEN.value).in_(
                        (CaseState.OPEN.value, CaseState.UNDER_REVIEW.value)
                    )
                ),
                func.count().filter(latest_verdict == "CONFIRMED_FRAUD"),
            )
            .select_from(EvaluationCaseRow)
            .join(EvaluationRow, EvaluationRow.evaluation_id == EvaluationCaseRow.assessment_id)
            .where(case_scope)
        ).one()
        return ConsoleSummary(
            as_of,
            int(transactions),
            int(today),
            int(evaluated),
            int(high_count),
            int(awaiting),
            int(confirmed),
            Decimal(suspicious),
        )
