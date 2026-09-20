"""Archive profile policy versions and seal each committed admission set."""

import sqlalchemy as sa
from alembic import op

revision = "0004_profile_revisions"
down_revision = "0003_history_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profile_revisions",
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("long_window_days", sa.Integer(), nullable=False),
        sa.Column("short_window_days", sa.Integer(), nullable=False),
        sa.Column(
            "writer_xid",
            sa.String(),
            nullable=False,
            server_default=sa.text("pg_current_xact_id()::text"),
        ),
        sa.PrimaryKeyConstraint("customer_id", "currency", "version"),
        sa.ForeignKeyConstraint(
            ["customer_id", "currency"], ["profiles.customer_id", "profiles.currency"]
        ),
        sa.CheckConstraint("version > 0", name="version"),
        sa.CheckConstraint(
            "short_window_days > 0 AND long_window_days >= short_window_days", name="windows"
        ),
    )
    # Earlier metadata was not retained. Capture only the real current head, never
    # invent historical policies or a wall-clock availability time for old versions.
    op.execute("""INSERT INTO profile_revisions
        (customer_id, currency, version, as_of, timezone, long_window_days, short_window_days)
        SELECT customer_id, currency, version, as_of, timezone, long_window_days, short_window_days
        FROM profiles""")
    op.execute("""CREATE FUNCTION fraudlens_capture_profile_revision() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            INSERT INTO profile_revisions
                (customer_id, currency, version, as_of, timezone,
                 long_window_days, short_window_days)
            VALUES (NEW.customer_id, NEW.currency, NEW.version, NEW.as_of, NEW.timezone,
                    NEW.long_window_days, NEW.short_window_days);
            RETURN NEW;
        END $$""")
    op.execute("""CREATE TRIGGER capture_profile_revision AFTER INSERT OR UPDATE ON profiles
        FOR EACH ROW EXECUTE FUNCTION fraudlens_capture_profile_revision()""")
    for event, level, name in (
        ("UPDATE OR DELETE", "ROW", "immutable_row"),
        ("TRUNCATE", "STATEMENT", "immutable_table"),
    ):
        op.execute(
            f"CREATE TRIGGER {name} BEFORE {event} ON profile_revisions "
            f"FOR EACH {level} EXECUTE FUNCTION fraudlens_reject_history_change()"
        )
    op.execute("""CREATE FUNCTION fraudlens_check_admission_revision() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM profile_revisions r
                JOIN transactions t ON t.transaction_id = NEW.transaction_id
                WHERE r.customer_id = NEW.customer_id AND r.currency = NEW.currency
                  AND r.version = NEW.admitted_version
                  AND r.writer_xid = pg_current_xact_id()::text
                  AND r.xmin = pg_current_xact_id()::xid
                  AND t.timestamp <= r.as_of
            ) THEN
                RAISE EXCEPTION 'admission requires a revision created in this transaction'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$""")
    # Repositories may flush observations before updating the head. Validate at commit,
    # when both exist. A later transaction cannot append to an already published version.
    op.execute("""CREATE CONSTRAINT TRIGGER admission_revision AFTER INSERT ON profile_observations
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
        EXECUTE FUNCTION fraudlens_check_admission_revision()""")


def downgrade() -> None:
    op.execute("DROP TRIGGER admission_revision ON profile_observations")
    op.execute("DROP FUNCTION fraudlens_check_admission_revision()")
    op.execute("DROP TRIGGER capture_profile_revision ON profiles")
    op.execute("DROP FUNCTION fraudlens_capture_profile_revision()")
    op.drop_table("profile_revisions")
