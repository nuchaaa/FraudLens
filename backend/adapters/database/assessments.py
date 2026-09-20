from dataclasses import asdict
from uuid import UUID

from backend.adapters.database.models import AssessmentRow, ModelRow, RuleRow, TransactionRow
from backend.adapters.database.repository_base import Repository
from backend.app.fraud.ports import ModelStatus, ModelVersion
from backend.app.risk.entities import RecommendedAction, RiskAssessment, RiskLevel, RiskReason
from backend.app.rules.contracts import RuleVersion


class PostgresModelRepository(Repository):
    def add(self, model: ModelVersion) -> None:
        self.session.add(ModelRow(**asdict(model)))
        self.session.flush()

    def get(self, version: str) -> ModelVersion | None:
        row = self.session.get(ModelRow, version)
        return (
            ModelVersion(
                row.version,
                row.feature_version,
                row.trained_at,
                row.artifact_sha256,
                ModelStatus(row.status),
                tuple((k, v) for k, v in row.metrics),
            )
            if row
            else None
        )


class PostgresRuleRepository(Repository):
    def add(self, rule: RuleVersion) -> None:
        self.session.add(RuleRow(**asdict(rule)))
        self.session.flush()

    def get(self, version: str) -> RuleVersion | None:
        row = self.session.get(RuleRow, version)
        return RuleVersion(row.version, row.description) if row else None


class PostgresAssessmentRepository(Repository):
    def add(self, assessment: RiskAssessment) -> None:
        tx = self.session.get(TransactionRow, assessment.transaction_id)
        if tx is None:
            raise ValueError("assessment requires a persisted transaction")
        self.session.add(
            AssessmentRow(**asdict(assessment), customer_id=tx.customer_id, currency=tx.currency)
        )
        self.session.flush()

    def get(self, assessment_id: UUID) -> RiskAssessment | None:
        row = self.session.get(AssessmentRow, assessment_id)
        if row is None:
            return None
        return RiskAssessment(
            row.assessment_id,
            row.transaction_id,
            row.profile_snapshot_id,
            row.score,
            RiskLevel(row.level),
            RecommendedAction(row.action),
            tuple(RiskReason(**r) for r in row.reasons),
            row.model_version,
            row.feature_version,
            row.rule_version,
            row.policy_version,
            row.strategy,
            row.timestamp,
        )
