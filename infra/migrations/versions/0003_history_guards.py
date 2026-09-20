"""Protect historical facts and enforce serialized case transitions in PostgreSQL."""

from alembic import op

revision = "0003_history_guards"
down_revision = "0002_persistence"
branch_labels = None
depends_on = None

HISTORICAL = (
    "customers",
    "transactions",
    "profile_observations",
    "profile_snapshots",
    "risk_assessments",
    "fraud_cases",
    "case_transitions",
    "analyst_decisions",
    "audit_events",
    "rule_versions",
    "idempotency_records",
)


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION fraudlens_reject_history_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'historical records are append-only: %', TG_TABLE_NAME
                USING ERRCODE = '23514';
        END $$
    """)
    for table in HISTORICAL:
        op.execute(
            f"CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION fraudlens_reject_history_change()"
        )
        op.execute(
            f"CREATE TRIGGER immutable_table BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION fraudlens_reject_history_change()"
        )
    op.execute("""
        CREATE FUNCTION fraudlens_check_transition() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE current_state text := 'OPEN'; last_sequence integer := 0;
                last_time timestamptz; last_record record;
        BEGIN
            SELECT created_at INTO last_time FROM fraud_cases
                WHERE case_id = NEW.case_id FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'case does not exist' USING ERRCODE = '23503';
            END IF;
            SELECT target, sequence, timestamp INTO last_record FROM case_transitions
                WHERE case_id = NEW.case_id ORDER BY sequence DESC LIMIT 1;
            IF FOUND THEN
                current_state := last_record.target;
                last_sequence := last_record.sequence;
                last_time := last_record.timestamp;
            END IF;
            IF NEW.previous <> current_state OR NEW.sequence <> last_sequence + 1
               OR NEW.timestamp < last_time OR NOT (
                (current_state = 'OPEN' AND NEW.target = 'UNDER_REVIEW') OR
                (current_state = 'UNDER_REVIEW'
                    AND NEW.target IN ('LEGITIMATE','CONFIRMED_FRAUD')) OR
                (current_state IN ('LEGITIMATE','CONFIRMED_FRAUD') AND NEW.target = 'CLOSED')
            ) THEN
                RAISE EXCEPTION 'invalid or stale case transition' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute(
        "CREATE TRIGGER valid_transition BEFORE INSERT ON case_transitions "
        "FOR EACH ROW EXECUTE FUNCTION fraudlens_check_transition()"
    )
    op.execute("""
        CREATE FUNCTION fraudlens_guard_outbox() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (to_jsonb(NEW) - 'attempts' - 'published_at') IS DISTINCT FROM
               (to_jsonb(OLD) - 'attempts' - 'published_at') OR NEW.attempts < OLD.attempts
               OR (OLD.published_at IS NOT NULL AND NEW IS DISTINCT FROM OLD) THEN
                RAISE EXCEPTION 'outbox envelope and publication are immutable'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute(
        "CREATE TRIGGER outbox_envelope BEFORE UPDATE ON outbox_events "
        "FOR EACH ROW EXECUTE FUNCTION fraudlens_guard_outbox()"
    )
    op.execute(
        "CREATE TRIGGER outbox_no_delete BEFORE DELETE ON outbox_events "
        "FOR EACH ROW EXECUTE FUNCTION fraudlens_reject_history_change()"
    )
    op.execute(
        "CREATE TRIGGER outbox_no_truncate BEFORE TRUNCATE ON outbox_events "
        "FOR EACH STATEMENT EXECUTE FUNCTION fraudlens_reject_history_change()"
    )
    op.execute("""
        CREATE FUNCTION fraudlens_guard_model() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (to_jsonb(NEW) - 'status') IS DISTINCT FROM (to_jsonb(OLD) - 'status') THEN
                RAISE EXCEPTION 'model provenance is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute(
        "CREATE TRIGGER model_provenance BEFORE UPDATE ON model_versions "
        "FOR EACH ROW EXECUTE FUNCTION fraudlens_guard_model()"
    )
    op.execute(
        "CREATE TRIGGER model_no_delete BEFORE DELETE ON model_versions "
        "FOR EACH ROW EXECUTE FUNCTION fraudlens_reject_history_change()"
    )
    op.execute(
        "CREATE TRIGGER model_no_truncate BEFORE TRUNCATE ON model_versions "
        "FOR EACH STATEMENT EXECUTE FUNCTION fraudlens_reject_history_change()"
    )
    op.execute("""
        CREATE FUNCTION fraudlens_guard_profile() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.customer_id <> OLD.customer_id OR NEW.currency <> OLD.currency
               OR NEW.version <> OLD.version + 1 OR NEW.as_of < OLD.as_of THEN
                RAISE EXCEPTION 'invalid profile version or identity change'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute(
        "CREATE TRIGGER profile_version BEFORE UPDATE ON profiles "
        "FOR EACH ROW EXECUTE FUNCTION fraudlens_guard_profile()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER profile_version ON profiles")
    op.execute("DROP FUNCTION fraudlens_guard_profile()")
    for trigger in ("model_provenance", "model_no_delete", "model_no_truncate"):
        op.execute(f"DROP TRIGGER {trigger} ON model_versions")
    op.execute("DROP FUNCTION fraudlens_guard_model()")
    for trigger in ("outbox_envelope", "outbox_no_delete", "outbox_no_truncate"):
        op.execute(f"DROP TRIGGER {trigger} ON outbox_events")
    op.execute("DROP FUNCTION fraudlens_guard_outbox()")
    op.execute("DROP TRIGGER valid_transition ON case_transitions")
    op.execute("DROP FUNCTION fraudlens_check_transition()")
    for table in HISTORICAL:
        op.execute(f"DROP TRIGGER immutable_row ON {table}")
        op.execute(f"DROP TRIGGER immutable_table ON {table}")
    op.execute("DROP FUNCTION fraudlens_reject_history_change()")
