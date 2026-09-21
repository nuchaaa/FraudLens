"""safe profile learning provenance"""

import sqlalchemy as sa
from alembic import op

revision = "0006_safe_profile_learning"
down_revision = "0005_experimental_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profile_learning_decisions",
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(100), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("profile_version_before", sa.Integer(), nullable=True),
        sa.Column("profile_version_after", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_json", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"]),
        sa.PrimaryKeyConstraint("decision_id"),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency"),
        sa.CheckConstraint("kind IN ('CASE_UPDATE','BOOTSTRAP')", name="kind"),
        sa.CheckConstraint(
            "action IN ('ACCEPT','QUARANTINE','REJECT_FROM_PROFILE')", name="action"
        ),
        sa.CheckConstraint(
            "profile_version_before IS NULL OR profile_version_before > 0",
            name="before_version",
        ),
        sa.CheckConstraint(
            "profile_version_after IS NULL OR profile_version_after > 0", name="after_version"
        ),
    )
    op.create_table(
        "profile_learning_evidence",
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("feedback_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["profile_learning_decisions.decision_id"]),
        sa.ForeignKeyConstraint(["case_id"], ["evaluation_cases.case_id"]),
        sa.ForeignKeyConstraint(["feedback_id"], ["evaluation_feedback.feedback_id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.transaction_id"]),
        sa.PrimaryKeyConstraint("decision_id", "case_id"),
        sa.UniqueConstraint("case_id"),
    )
    for table in ("profile_learning_decisions", "profile_learning_evidence"):
        op.execute(
            f"CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION fraudlens_reject_history_change()"
        )
        op.execute(
            f"CREATE TRIGGER immutable_table BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION fraudlens_reject_history_change()"
        )

    op.add_column(
        "profiles",
        sa.Column(
            "admission_workflow_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("profiles", sa.Column("admission_policy_version", sa.String(100)))
    op.add_column("profiles", sa.Column("learning_decision_id", sa.Uuid()))
    op.create_check_constraint(
        op.f("ck_profiles_admission_provenance"),
        "profiles",
        "admission_workflow_verified = "
        "(admission_policy_version IS NOT NULL AND learning_decision_id IS NOT NULL)",
    )
    op.create_foreign_key(
        op.f("fk_profiles_learning_decision_id_profile_learning_decisions"),
        "profiles",
        "profile_learning_decisions",
        ["learning_decision_id"],
        ["decision_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.add_column(
        "profile_revisions",
        sa.Column(
            "admission_workflow_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("profile_revisions", sa.Column("admission_policy_version", sa.String(100)))
    op.add_column("profile_revisions", sa.Column("learning_decision_id", sa.Uuid()))
    op.create_check_constraint(
        op.f("ck_profile_revisions_admission_provenance"),
        "profile_revisions",
        "admission_workflow_verified = "
        "(admission_policy_version IS NOT NULL AND learning_decision_id IS NOT NULL)",
    )
    op.create_foreign_key(
        op.f("fk_profile_revisions_learning_decision_id_profile_learning_decisions"),
        "profile_revisions",
        "profile_learning_decisions",
        ["learning_decision_id"],
        ["decision_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.execute("""CREATE OR REPLACE FUNCTION fraudlens_capture_profile_revision() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
INSERT INTO profile_revisions
(customer_id,currency,version,as_of,timezone,long_window_days,short_window_days,
 admission_workflow_verified,admission_policy_version,learning_decision_id)
VALUES (NEW.customer_id,NEW.currency,NEW.version,NEW.as_of,NEW.timezone,
NEW.long_window_days,NEW.short_window_days,NEW.admission_workflow_verified,
NEW.admission_policy_version,NEW.learning_decision_id); RETURN NEW; END $$""")

    op.execute("""CREATE FUNCTION fraudlens_check_learning_envelope() RETURNS trigger
LANGUAGE plpgsql AS $$ DECLARE doc jsonb := NEW.response_json::jsonb; BEGIN
IF doc->>'schema_version' IS DISTINCT FROM 'profile-learning-decision-v1'
 OR doc->>'decision_id' IS DISTINCT FROM NEW.decision_id::text
 OR doc->>'customer_id' IS DISTINCT FROM NEW.customer_id::text
 OR doc->>'currency' IS DISTINCT FROM NEW.currency
 OR doc->>'actor_id' IS DISTINCT FROM NEW.actor_id::text
 OR doc->>'kind' IS DISTINCT FROM NEW.kind
 OR doc->>'action' IS DISTINCT FROM NEW.action
 OR doc->>'reason' IS DISTINCT FROM NEW.reason
 OR doc->>'policy_version' IS DISTINCT FROM NEW.policy_version
 OR (doc->>'created_at')::timestamptz IS DISTINCT FROM NEW.created_at
 OR doc->'profile_version_before' IS DISTINCT FROM
    coalesce(to_jsonb(NEW.profile_version_before),'null'::jsonb)
 OR doc->'profile_version_after' IS DISTINCT FROM
    coalesce(to_jsonb(NEW.profile_version_after),'null'::jsonb)
 OR jsonb_typeof(doc->'evidence') IS DISTINCT FROM 'array'
 OR (doc->>'admission_workflow_verified')::boolean IS DISTINCT FROM (NEW.action='ACCEPT')
 OR doc->>'experimental' IS DISTINCT FROM 'true'
 OR doc->>'low_weight_applied' IS DISTINCT FROM 'false'
 OR doc->>'correction_applied' IS DISTINCT FROM 'false'
THEN RAISE EXCEPTION 'inconsistent learning decision envelope' USING ERRCODE='23514';
END IF; RETURN NEW; END $$""")
    op.execute("""CREATE TRIGGER valid_learning_envelope BEFORE INSERT ON
profile_learning_decisions FOR EACH ROW EXECUTE FUNCTION fraudlens_check_learning_envelope()""")

    op.execute("""CREATE FUNCTION fraudlens_check_learning_evidence() RETURNS trigger
LANGUAGE plpgsql AS $$ DECLARE d record; c record; e record; f record; latest text; BEGIN
SELECT * INTO d FROM profile_learning_decisions WHERE decision_id=NEW.decision_id;
SELECT * INTO c FROM evaluation_cases WHERE case_id=NEW.case_id;
SELECT * INTO e FROM experimental_evaluations WHERE evaluation_id=c.assessment_id;
SELECT * INTO f FROM evaluation_feedback WHERE feedback_id=NEW.feedback_id
AND case_id=NEW.case_id;
SELECT target INTO latest FROM evaluation_case_transitions WHERE case_id=NEW.case_id
ORDER BY sequence DESC LIMIT 1;
IF d IS NULL OR c IS NULL OR e IS NULL OR f IS NULL OR latest IS DISTINCT FROM 'CLOSED'
 OR NEW.transaction_id IS DISTINCT FROM c.transaction_id
 OR NEW.transaction_id IS DISTINCT FROM e.transaction_id
 OR NEW.reviewer_id IS DISTINCT FROM f.actor_id
 OR d.actor_id=NEW.reviewer_id OR d.customer_id IS DISTINCT FROM e.customer_id
 OR d.currency IS DISTINCT FROM e.currency
 OR f.verdict NOT IN ('LEGITIMATE','CONFIRMED_FRAUD')
 OR (d.kind='BOOTSTRAP' AND (f.verdict<>'LEGITIMATE' OR d.action<>'ACCEPT'))
 OR (d.kind='CASE_UPDATE' AND
    ((f.verdict='CONFIRMED_FRAUD' AND d.action<>'REJECT_FROM_PROFILE') OR
     (f.verdict='LEGITIMATE' AND d.action NOT IN ('ACCEPT','QUARANTINE'))))
THEN RAISE EXCEPTION 'invalid profile learning evidence' USING ERRCODE='23514';
END IF; RETURN NEW; END $$""")
    op.execute("""CREATE TRIGGER valid_learning_evidence BEFORE INSERT ON
profile_learning_evidence FOR EACH ROW EXECUTE FUNCTION fraudlens_check_learning_evidence()""")

    op.execute("""CREATE FUNCTION fraudlens_require_learning_evidence() RETURNS trigger
LANGUAGE plpgsql AS $$ DECLARE evidence_count integer; reviewer_count integer;
doc jsonb := NEW.response_json::jsonb; BEGIN
SELECT count(*),count(DISTINCT reviewer_id) INTO evidence_count,reviewer_count
FROM profile_learning_evidence WHERE decision_id=NEW.decision_id;
IF (NEW.kind='CASE_UPDATE' AND evidence_count<>1)
 OR (NEW.kind='BOOTSTRAP' AND (evidence_count<5 OR evidence_count>100 OR reviewer_count<2))
 OR jsonb_array_length(doc->'evidence')<>evidence_count
 OR EXISTS (SELECT 1 FROM profile_learning_evidence e WHERE e.decision_id=NEW.decision_id
    AND NOT (doc->'evidence' @> jsonb_build_array(jsonb_build_object(
      'case_id',e.case_id::text,'feedback_id',e.feedback_id::text,
      'transaction_id',e.transaction_id::text,'reviewer_id',e.reviewer_id::text))))
 OR (NEW.action='ACCEPT' AND NEW.profile_version_after IS DISTINCT FROM
     coalesce(NEW.profile_version_before,0)+1)
 OR (NEW.action<>'ACCEPT' AND NEW.profile_version_after IS DISTINCT FROM
     NEW.profile_version_before)
THEN RAISE EXCEPTION 'learning evidence or version contract incomplete' USING ERRCODE='23514';
END IF; RETURN NEW; END $$""")
    op.execute("""CREATE CONSTRAINT TRIGGER complete_learning_decision AFTER INSERT ON
profile_learning_decisions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION fraudlens_require_learning_evidence()""")

    op.execute("""CREATE FUNCTION fraudlens_check_profile_learning_provenance() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
IF NEW.admission_workflow_verified AND NOT EXISTS (
 SELECT 1 FROM profile_learning_decisions d WHERE d.decision_id=NEW.learning_decision_id
 AND d.customer_id=NEW.customer_id AND d.currency=NEW.currency AND d.action='ACCEPT'
 AND d.policy_version=NEW.admission_policy_version AND d.profile_version_after=NEW.version
) THEN RAISE EXCEPTION 'verified profile needs matching learning decision' USING ERRCODE='23514';
END IF; RETURN NEW; END $$""")
    op.execute("""CREATE CONSTRAINT TRIGGER verified_learning_provenance AFTER INSERT OR UPDATE
ON profiles DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION fraudlens_check_profile_learning_provenance()""")


def downgrade() -> None:
    op.execute("DROP TRIGGER verified_learning_provenance ON profiles")
    op.execute("DROP FUNCTION fraudlens_check_profile_learning_provenance()")
    op.execute("""CREATE OR REPLACE FUNCTION fraudlens_capture_profile_revision() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
INSERT INTO profile_revisions
(customer_id,currency,version,as_of,timezone,long_window_days,short_window_days)
VALUES (NEW.customer_id,NEW.currency,NEW.version,NEW.as_of,NEW.timezone,
NEW.long_window_days,NEW.short_window_days); RETURN NEW; END $$""")
    op.drop_constraint(
        op.f("fk_profile_revisions_learning_decision_id_profile_learning_decisions"),
        "profile_revisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("ck_profile_revisions_admission_provenance"),
        "profile_revisions",
        type_="check",
    )
    op.drop_column("profile_revisions", "learning_decision_id")
    op.drop_column("profile_revisions", "admission_policy_version")
    op.drop_column("profile_revisions", "admission_workflow_verified")
    op.drop_constraint(
        op.f("fk_profiles_learning_decision_id_profile_learning_decisions"),
        "profiles",
        type_="foreignkey",
    )
    op.drop_constraint(op.f("ck_profiles_admission_provenance"), "profiles", type_="check")
    op.drop_column("profiles", "learning_decision_id")
    op.drop_column("profiles", "admission_policy_version")
    op.drop_column("profiles", "admission_workflow_verified")
    op.drop_table("profile_learning_evidence")
    op.drop_table("profile_learning_decisions")
    op.execute("DROP FUNCTION fraudlens_require_learning_evidence()")
    op.execute("DROP FUNCTION fraudlens_check_learning_evidence()")
    op.execute("DROP FUNCTION fraudlens_check_learning_envelope()")
