"""Durable leased delivery and immutable local consumer receipts."""

from alembic import op

revision = "0007_outbox_delivery"
down_revision = "0006_safe_profile_learning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE outbox_delivery (
            event_id uuid CONSTRAINT pk_outbox_delivery PRIMARY KEY,
            token uuid, lease_until timestamptz, available_at timestamptz NOT NULL,
            completed_at timestamptz, dead_at timestamptz, last_error varchar(40),
            CONSTRAINT fk_outbox_delivery_event_id_outbox_events FOREIGN KEY (event_id)
                REFERENCES outbox_events(event_id),
            CONSTRAINT ck_outbox_delivery_lease_pair CHECK
                ((token IS NULL) = (lease_until IS NULL)),
            CONSTRAINT ck_outbox_delivery_terminal CHECK
                (completed_at IS NULL OR dead_at IS NULL),
            CONSTRAINT ck_outbox_delivery_terminal_lease CHECK
                ((completed_at IS NULL AND dead_at IS NULL) OR token IS NULL)
        );
        CREATE INDEX ix_outbox_delivery_due ON outbox_delivery(available_at);
        CREATE TABLE consumer_receipts (
            consumer_id varchar(100) NOT NULL, event_id uuid NOT NULL,
            recorded_at timestamptz NOT NULL,
            CONSTRAINT pk_consumer_receipts PRIMARY KEY (consumer_id,event_id),
            CONSTRAINT fk_consumer_receipts_event_id_outbox_events FOREIGN KEY (event_id)
                REFERENCES outbox_events(event_id)
        );
        INSERT INTO outbox_delivery(event_id,available_at,completed_at)
            SELECT event_id, GREATEST(clock_timestamp(),occurred_at), published_at
            FROM outbox_events;
        CREATE FUNCTION fraudlens_initialize_delivery() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            INSERT INTO outbox_delivery(event_id,available_at,completed_at)
                VALUES(NEW.event_id,GREATEST(clock_timestamp(),NEW.occurred_at),NEW.published_at);
            RETURN NEW;
        END $$;
        CREATE TRIGGER initialize_delivery AFTER INSERT ON outbox_events
            FOR EACH ROW EXECUTE FUNCTION fraudlens_initialize_delivery();
        CREATE FUNCTION fraudlens_guard_delivery() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.event_id IS DISTINCT FROM OLD.event_id OR
                ((OLD.completed_at IS NOT NULL OR OLD.dead_at IS NOT NULL)
                 AND NEW IS DISTINCT FROM OLD) THEN
                RAISE EXCEPTION 'terminal delivery and identity are immutable'
                    USING ERRCODE='23514';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER delivery_terminal BEFORE UPDATE ON outbox_delivery
            FOR EACH ROW EXECUTE FUNCTION fraudlens_guard_delivery();
    """)
    for table, operations in (
        ("outbox_delivery", ("DELETE", "TRUNCATE")),
        ("consumer_receipts", ("UPDATE", "DELETE", "TRUNCATE")),
    ):
        for operation in operations:
            level = "STATEMENT" if operation == "TRUNCATE" else "ROW"
            op.execute(
                f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} ON {table} "
                f"FOR EACH {level} EXECUTE FUNCTION fraudlens_reject_history_change()"
            )


def downgrade() -> None:
    op.execute("DROP TRIGGER initialize_delivery ON outbox_events")
    op.execute("DROP FUNCTION fraudlens_initialize_delivery()")
    op.drop_table("consumer_receipts")
    op.drop_table("outbox_delivery")
    op.execute("DROP FUNCTION fraudlens_guard_delivery()")
