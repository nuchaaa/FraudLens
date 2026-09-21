"""experimental reviews"""

import sqlalchemy as sa
from alembic import op

revision = "0005_experimental_reviews"
down_revision = "0004_profile_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "experimental_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_json", sa.String(), nullable=False),
        sa.CheckConstraint(
            "((response_json::jsonb->>'production_eligible') = 'false' AND "
            "(response_json::jsonb->>'schema_version') = 'experimental-evaluation-v1') IS TRUE",
            name=op.f("ck_experimental_evaluations_experimental"),
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id", "customer_id", "currency"],
            ["transactions.transaction_id", "transactions.customer_id", "transactions.currency"],
            name=op.f("fk_experimental_evaluations_transaction_id_transactions"),
        ),
        sa.PrimaryKeyConstraint("evaluation_id", name=op.f("pk_experimental_evaluations")),
        sa.UniqueConstraint(
            "evaluation_id",
            "transaction_id",
            name=op.f("uq_experimental_evaluations_evaluation_id"),
        ),
    )
    op.create_table(
        "evaluation_cases",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id", "transaction_id"],
            ["experimental_evaluations.evaluation_id", "experimental_evaluations.transaction_id"],
            name=op.f("fk_evaluation_cases_assessment_id_experimental_evaluations"),
        ),
        sa.PrimaryKeyConstraint("case_id", name=op.f("pk_evaluation_cases")),
        sa.UniqueConstraint("assessment_id", name=op.f("uq_evaluation_cases_assessment_id")),
    )
    op.create_table(
        "evaluation_case_transitions",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("previous", sa.String(length=30), nullable=False),
        sa.Column("target", sa.String(length=30), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sequence > 0", name=op.f("ck_evaluation_case_transitions_sequence")),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["evaluation_cases.case_id"],
            name=op.f("fk_evaluation_case_transitions_case_id_evaluation_cases"),
        ),
        sa.PrimaryKeyConstraint("case_id", "sequence", name=op.f("pk_evaluation_case_transitions")),
    )
    op.create_table(
        "evaluation_feedback",
        sa.Column("feedback_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("verdict", sa.String(length=30), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("comment", sa.String(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "verdict IN ('CONFIRMED_FRAUD','LEGITIMATE','NEEDS_INVESTIGATION')",
            name=op.f("ck_evaluation_feedback_verdict"),
        ),
        sa.CheckConstraint(
            "length(trim(comment)) > 0 AND length(comment) <= 2000",
            name=op.f("ck_evaluation_feedback_comment"),
        ),
        sa.CheckConstraint("sequence > 0", name=op.f("ck_evaluation_feedback_sequence")),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["evaluation_cases.case_id"],
            name=op.f("fk_evaluation_feedback_case_id_evaluation_cases"),
        ),
        sa.PrimaryKeyConstraint("feedback_id", name=op.f("pk_evaluation_feedback")),
        sa.UniqueConstraint("case_id", "sequence", name=op.f("uq_evaluation_feedback_case_id")),
    )

    for table in (
        "experimental_evaluations",
        "evaluation_cases",
        "evaluation_case_transitions",
        "evaluation_feedback",
    ):
        op.execute(
            f"CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION fraudlens_reject_history_change()"
        )
        op.execute(
            f"CREATE TRIGGER immutable_table BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION fraudlens_reject_history_change()"
        )
    op.execute("""CREATE FUNCTION fraudlens_check_evaluation_envelope() RETURNS trigger
    LANGUAGE plpgsql AS $$ DECLARE doc jsonb := NEW.response_json::jsonb; BEGIN
        IF doc->>'evaluation_id' IS DISTINCT FROM NEW.evaluation_id::text
           OR doc->>'transaction_id' IS DISTINCT FROM NEW.transaction_id::text
           OR doc->>'customer_id' IS DISTINCT FROM NEW.customer_id::text
           OR doc->>'currency' IS DISTINCT FROM NEW.currency
           OR doc->>'actor_id' IS DISTINCT FROM NEW.actor_id::text
           OR (doc->>'created_at')::timestamptz IS DISTINCT FROM NEW.created_at
           OR doc->'risk'->>'production_eligible' IS DISTINCT FROM 'false'
           OR doc->'risk'->>'operational_action_executed' IS DISTINCT FROM 'false'
           OR doc->'risk'->>'transaction_id' IS DISTINCT FROM NEW.transaction_id::text
           OR doc->'risk'->>'status' IS NULL
           OR doc->'risk'->>'status' NOT IN ('SCORED', 'INSUFFICIENT_EVIDENCE')
           OR jsonb_typeof(doc->'context_artifact') IS DISTINCT FROM 'object'
           OR jsonb_typeof(doc->'explanation') IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'inconsistent experimental envelope' USING ERRCODE='23514';
        END IF;
        IF doc->'risk'->>'status' = 'INSUFFICIENT_EVIDENCE' THEN
            IF doc->'risk'->'score' IS DISTINCT FROM 'null'::jsonb
               OR doc->'risk'->'level' IS DISTINCT FROM 'null'::jsonb
               OR doc->'risk'->'suggested_action' IS DISTINCT FROM 'null'::jsonb THEN
                RAISE EXCEPTION 'insufficient evidence cannot have a decision'
                    USING ERRCODE='23514';
            END IF;
        ELSIF jsonb_typeof(doc->'risk'->'score') IS DISTINCT FROM 'number'
              OR (doc->'risk'->>'score')::numeric NOT BETWEEN 0 AND 1 THEN
            RAISE EXCEPTION 'scored evaluation needs a finite score' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END $$""")
    op.execute(
        """CREATE TRIGGER valid_envelope BEFORE INSERT ON experimental_evaluations FOR EACH ROW
EXECUTE FUNCTION fraudlens_check_evaluation_envelope()"""
    )
    op.execute("""CREATE FUNCTION fraudlens_check_evaluation_transition() RETURNS trigger
LANGUAGE plpgsql AS $$ DECLARE current_state text := 'OPEN'; last_sequence integer :=
0;
last_time timestamptz; item record;
BEGIN
SELECT created_at INTO last_time FROM evaluation_cases WHERE case_id=NEW.case_id FOR
UPDATE;
IF NOT FOUND THEN RAISE EXCEPTION 'missing case' USING ERRCODE='23503'; END IF;
SELECT * INTO item FROM evaluation_case_transitions WHERE case_id=NEW.case_id ORDER BY
sequence DESC LIMIT 1;
IF FOUND THEN current_state:=item.target; last_sequence:=item.sequence;
last_time:=item.timestamp; END IF;
SELECT greatest(last_time, max(timestamp)) INTO last_time FROM evaluation_feedback
WHERE case_id=NEW.case_id;
IF NEW.previous<>current_state OR NEW.sequence<>last_sequence+1 OR
NEW.timestamp<last_time OR NOT (
(current_state='OPEN' AND NEW.target='UNDER_REVIEW') OR
(current_state='UNDER_REVIEW' AND NEW.target IN ('LEGITIMATE','CONFIRMED_FRAUD')) OR
(current_state IN ('LEGITIMATE','CONFIRMED_FRAUD') AND NEW.target='CLOSED')
) THEN RAISE EXCEPTION 'invalid review transition' USING ERRCODE='23514'; END IF;
RETURN NEW;
END $$""")
    op.execute(
        """CREATE TRIGGER valid_transition BEFORE INSERT ON evaluation_case_transitions FOR EACH
ROW EXECUTE FUNCTION fraudlens_check_evaluation_transition()"""
    )
    op.execute("""CREATE FUNCTION fraudlens_check_evaluation_feedback() RETURNS trigger
LANGUAGE plpgsql AS $$ DECLARE last_transition record; last_sequence integer;
last_time timestamptz;
BEGIN
PERFORM 1 FROM evaluation_cases WHERE case_id=NEW.case_id FOR UPDATE;
SELECT * INTO last_transition FROM evaluation_case_transitions WHERE
case_id=NEW.case_id ORDER BY sequence DESC LIMIT 1;
IF NOT FOUND THEN RAISE EXCEPTION 'feedback needs review' USING ERRCODE='23514'; END
IF;
SELECT coalesce(max(sequence),0), max(timestamp) INTO last_sequence,last_time FROM
evaluation_feedback WHERE case_id=NEW.case_id;
IF NEW.sequence<>last_sequence+1 OR
NEW.timestamp<greatest(last_time,last_transition.timestamp) OR NOT (
(NEW.verdict='NEEDS_INVESTIGATION' AND last_transition.target='UNDER_REVIEW') OR
(NEW.verdict IN ('LEGITIMATE','CONFIRMED_FRAUD') AND
last_transition.target=NEW.verdict
AND last_transition.actor_id=NEW.actor_id AND last_transition.timestamp=NEW.timestamp
AND NOT EXISTS (SELECT 1 FROM evaluation_feedback WHERE case_id=NEW.case_id AND
verdict IN ('LEGITIMATE','CONFIRMED_FRAUD')))
) THEN RAISE EXCEPTION 'invalid feedback provenance or state' USING ERRCODE='23514';
END IF;
RETURN NEW;
END $$""")
    op.execute(
        """CREATE TRIGGER valid_feedback BEFORE INSERT ON evaluation_feedback FOR EACH ROW
EXECUTE FUNCTION fraudlens_check_evaluation_feedback()"""
    )
    op.execute("""CREATE FUNCTION fraudlens_require_review_feedback() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
IF NEW.target IN ('LEGITIMATE','CONFIRMED_FRAUD') AND NOT EXISTS (
SELECT 1 FROM evaluation_feedback WHERE case_id=NEW.case_id AND actor_id=NEW.actor_id
AND timestamp=NEW.timestamp AND verdict=NEW.target
) THEN RAISE EXCEPTION 'terminal review needs matching feedback' USING
ERRCODE='23514'; END IF;
RETURN NEW;
END $$""")
    op.execute(
        """CREATE CONSTRAINT TRIGGER terminal_feedback AFTER INSERT ON
evaluation_case_transitions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE
FUNCTION fraudlens_require_review_feedback()"""
    )


def downgrade() -> None:
    op.drop_table("evaluation_feedback")
    op.drop_table("evaluation_case_transitions")
    op.drop_table("evaluation_cases")
    op.drop_table("experimental_evaluations")

    op.execute("DROP FUNCTION fraudlens_require_review_feedback()")
    op.execute("DROP FUNCTION fraudlens_check_evaluation_feedback()")
    op.execute("DROP FUNCTION fraudlens_check_evaluation_transition()")
    op.execute("DROP FUNCTION fraudlens_check_evaluation_envelope()")
