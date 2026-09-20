"""Typed PostgreSQL mappings. Historical facts are protected by migration triggers."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.adapters.database.base import Base


class CustomerRow(Base):
    __tablename__ = "customers"
    customer_id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(100))


class TransactionRow(Base):
    __tablename__ = "transactions"
    transaction_id: Mapped[UUID] = mapped_column(primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.customer_id"))
    recipient_id: Mapped[UUID]
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(String(20))
    device_id: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))
    __table_args__ = (
        CheckConstraint("amount > 0 AND amount < 'Infinity'::numeric", name="amount_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency"),
        CheckConstraint("channel IN ('MOBILE','WEB','ATM','BRANCH')", name="channel"),
        CheckConstraint("status IN ('RECEIVED','EVALUATED')", name="status"),
        CheckConstraint("length(trim(device_id)) > 0", name="device"),
        UniqueConstraint("transaction_id", "customer_id", "currency"),
        Index("ix_transactions_customer_time", "customer_id", "timestamp"),
    )


class ProfileRow(Base):
    __tablename__ = "profiles"
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.customer_id"), primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    version: Mapped[int]
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(100))
    long_window_days: Mapped[int]
    short_window_days: Mapped[int]
    __table_args__ = (
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency"),
        CheckConstraint("version > 0", name="version"),
        CheckConstraint(
            "short_window_days > 0 AND long_window_days >= short_window_days", name="windows"
        ),
    )


class ProfileRevisionRow(Base):
    __tablename__ = "profile_revisions"
    customer_id: Mapped[UUID] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(100))
    long_window_days: Mapped[int]
    short_window_days: Mapped[int]
    writer_xid: Mapped[str] = mapped_column(server_default=text("pg_current_xact_id()::text"))
    __table_args__ = (
        ForeignKeyConstraint(
            ["customer_id", "currency"], ["profiles.customer_id", "profiles.currency"]
        ),
        CheckConstraint("version > 0", name="version"),
        CheckConstraint(
            "short_window_days > 0 AND long_window_days >= short_window_days", name="windows"
        ),
    )


class ObservationRow(Base):
    __tablename__ = "profile_observations"
    transaction_id: Mapped[UUID] = mapped_column(primary_key=True)
    customer_id: Mapped[UUID]
    currency: Mapped[str] = mapped_column(String(3))
    admitted_version: Mapped[int]
    ordinal: Mapped[int]
    __table_args__ = (
        ForeignKeyConstraint(
            ["customer_id", "currency"], ["profiles.customer_id", "profiles.currency"]
        ),
        ForeignKeyConstraint(
            ["transaction_id", "customer_id", "currency"],
            ["transactions.transaction_id", "transactions.customer_id", "transactions.currency"],
        ),
        CheckConstraint("admitted_version > 0 AND ordinal >= 0", name="position"),
        UniqueConstraint("customer_id", "currency", "ordinal"),
    )


class ModelRow(Base):
    __tablename__ = "model_versions"
    version: Mapped[str] = mapped_column(String(100), primary_key=True)
    feature_version: Mapped[str] = mapped_column(String(100))
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    artifact_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20))
    metrics: Mapped[list[list[Any]]] = mapped_column(JSONB)
    __table_args__ = (
        UniqueConstraint("version", "feature_version"),
        CheckConstraint("artifact_sha256 ~ '^[0-9a-f]{64}$'", name="digest"),
        CheckConstraint("status IN ('CANDIDATE','PRODUCTION','ARCHIVED')", name="status"),
        Index(
            "uq_one_production_model",
            "status",
            unique=True,
            postgresql_where=text("status = 'PRODUCTION'"),
        ),
    )


class RuleRow(Base):
    __tablename__ = "rule_versions"
    version: Mapped[str] = mapped_column(String(100), primary_key=True)
    description: Mapped[str]


class SnapshotRow(Base):
    __tablename__ = "profile_snapshots"
    snapshot_id: Mapped[UUID] = mapped_column(primary_key=True)
    assessment_id: Mapped[UUID] = mapped_column(unique=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.customer_id"))
    currency: Mapped[str] = mapped_column(String(3))
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB)
    __table_args__ = (
        UniqueConstraint("snapshot_id", "assessment_id", "customer_id", "currency"),
        ForeignKeyConstraint(
            ["assessment_id"],
            ["risk_assessments.assessment_id"],
            name="fk_snapshot_assessment",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
    )


class AssessmentRow(Base):
    __tablename__ = "risk_assessments"
    assessment_id: Mapped[UUID] = mapped_column(primary_key=True)
    transaction_id: Mapped[UUID]
    customer_id: Mapped[UUID]
    currency: Mapped[str] = mapped_column(String(3))
    profile_snapshot_id: Mapped[UUID]
    score: Mapped[float]
    level: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(30))
    reasons: Mapped[list[dict[str, str]]] = mapped_column(JSONB)
    model_version: Mapped[str] = mapped_column(String(100))
    feature_version: Mapped[str] = mapped_column(String(100))
    rule_version: Mapped[str] = mapped_column(ForeignKey("rule_versions.version"))
    policy_version: Mapped[str] = mapped_column(String(100))
    strategy: Mapped[str] = mapped_column(String(100))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("assessment_id", "transaction_id", name="uq_assessment_transaction"),
        UniqueConstraint(
            "assessment_id",
            "transaction_id",
            "model_version",
            name="uq_assessment_transaction_model",
        ),
        ForeignKeyConstraint(
            ["transaction_id", "customer_id", "currency"],
            ["transactions.transaction_id", "transactions.customer_id", "transactions.currency"],
        ),
        ForeignKeyConstraint(
            ["profile_snapshot_id", "assessment_id", "customer_id", "currency"],
            [
                "profile_snapshots.snapshot_id",
                "profile_snapshots.assessment_id",
                "profile_snapshots.customer_id",
                "profile_snapshots.currency",
            ],
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["model_version", "feature_version"],
            ["model_versions.version", "model_versions.feature_version"],
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="score"),
        CheckConstraint(
            "(level, action) IN (('LOW','ALLOW'), ('MEDIUM','STEP_UP_VERIFICATION'), "
            "('HIGH','HOLD_AND_REVIEW'), ('CRITICAL','URGENT_REVIEW'))",
            name="decision",
        ),
        Index("ix_assessments_transaction", "transaction_id"),
    )


class CaseRow(Base):
    __tablename__ = "fraud_cases"
    case_id: Mapped[UUID] = mapped_column(primary_key=True)
    transaction_id: Mapped[UUID]
    assessment_id: Mapped[UUID] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["assessment_id", "transaction_id"],
            ["risk_assessments.assessment_id", "risk_assessments.transaction_id"],
        ),
    )


class TransitionRow(Base):
    __tablename__ = "case_transitions"
    case_id: Mapped[UUID] = mapped_column(ForeignKey("fraud_cases.case_id"), primary_key=True)
    sequence: Mapped[int] = mapped_column(primary_key=True)
    previous: Mapped[str] = mapped_column(String(30))
    target: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[UUID]
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("sequence > 0", name="sequence"),)


class FeedbackRow(Base):
    __tablename__ = "analyst_decisions"
    decision_id: Mapped[UUID] = mapped_column(primary_key=True)
    transaction_id: Mapped[UUID]
    assessment_id: Mapped[UUID]
    analyst_id: Mapped[UUID]
    verdict: Mapped[str] = mapped_column(String(30))
    model_prediction: Mapped[float]
    model_version: Mapped[str] = mapped_column(String(100))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    comment: Mapped[str]
    __table_args__ = (
        ForeignKeyConstraint(
            ["assessment_id", "transaction_id", "model_version"],
            [
                "risk_assessments.assessment_id",
                "risk_assessments.transaction_id",
                "risk_assessments.model_version",
            ],
        ),
        CheckConstraint("model_prediction >= 0 AND model_prediction <= 1", name="prediction"),
        CheckConstraint(
            "verdict IN ('CONFIRMED_FRAUD','LEGITIMATE','NEEDS_INVESTIGATION')", name="verdict"
        ),
        CheckConstraint("length(trim(comment)) > 0", name="comment"),
    )


class AuditRow(Base):
    __tablename__ = "audit_events"
    audit_id: Mapped[UUID] = mapped_column(primary_key=True)
    actor_id: Mapped[UUID]
    action: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[UUID] = mapped_column(index=True)
    correlation_id: Mapped[UUID] = mapped_column(index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    detail: Mapped[str]


class OutboxRow(Base):
    __tablename__ = "outbox_events"
    event_id: Mapped[UUID] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100))
    aggregate_id: Mapped[UUID]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[UUID]
    payload: Mapped[list[list[str]]] = mapped_column(JSONB)
    schema_version: Mapped[int]
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("attempts >= 0 AND schema_version > 0", name="versions"),
        CheckConstraint("published_at IS NULL OR published_at >= occurred_at", name="publication"),
        Index("ix_outbox_pending", "occurred_at", postgresql_where=text("published_at IS NULL")),
    )


class IdempotencyRow(Base):
    __tablename__ = "idempotency_records"
    principal_id: Mapped[UUID] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    request_sha256: Mapped[str] = mapped_column(String(64))
    transaction_id: Mapped[UUID] = mapped_column(ForeignKey("transactions.transaction_id"))
    response_json: Mapped[str]
    status_code: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("request_sha256 ~ '^[0-9a-f]{64}$'", name="digest"),
        CheckConstraint("status_code >= 200 AND status_code < 300", name="status"),
        CheckConstraint("length(key) > 0 AND key = trim(key)", name="key"),
    )
