from dataclasses import asdict
from uuid import UUID

from sqlalchemy import select

from backend.adapters.database.models import ProfileLearningDecisionRow, ProfileLearningEvidenceRow
from backend.adapters.database.repository_base import Repository
from backend.app.profile.gate import ProfileUpdateAction
from backend.app.profile.learning import LearningDecision, LearningEvidence, LearningKind


class PostgresProfileLearningRepository(Repository):
    def get(self, decision_id: UUID) -> LearningDecision | None:
        row = self.session.get(ProfileLearningDecisionRow, decision_id)
        if row is None:
            return None
        evidence_rows = self.session.scalars(
            select(ProfileLearningEvidenceRow)
            .where(ProfileLearningEvidenceRow.decision_id == decision_id)
            .order_by(ProfileLearningEvidenceRow.case_id)
        ).all()
        return LearningDecision(
            row.decision_id,
            row.customer_id,
            row.currency,
            row.actor_id,
            LearningKind(row.kind),
            ProfileUpdateAction(row.action),
            row.reason,
            row.policy_version,
            row.profile_version_before,
            row.profile_version_after,
            row.created_at,
            row.response_json,
            tuple(
                LearningEvidence(
                    item.case_id,
                    item.feedback_id,
                    item.transaction_id,
                    item.reviewer_id,
                )
                for item in evidence_rows
            ),
        )

    def add(self, decision: LearningDecision) -> None:
        values = asdict(decision)
        evidence = values.pop("evidence")
        values["kind"] = decision.kind.value
        values["action"] = decision.action.value
        self.session.add(ProfileLearningDecisionRow(**values))
        self.session.flush()
        for item in evidence:
            self.session.add(ProfileLearningEvidenceRow(decision_id=decision.decision_id, **item))
        self.session.flush()
