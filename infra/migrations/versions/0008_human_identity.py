"""Opaque human sessions, bounded shared throttles and immutable refresh/audit facts."""

from alembic import op

revision = "0008_human_identity"
down_revision = "0007_outbox_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE human_accounts (
            account_id uuid CONSTRAINT pk_human_accounts PRIMARY KEY,
            login varchar(64) NOT NULL CONSTRAINT uq_human_accounts_login UNIQUE,
            password_hash varchar(255) NOT NULL,
            role varchar(20) NOT NULL,
            customer_ids uuid[] NOT NULL DEFAULT '{}',
            active boolean NOT NULL, authorization_version integer NOT NULL,
            expires_at timestamptz, created_at timestamptz NOT NULL,
            updated_at timestamptz NOT NULL,
            CONSTRAINT ck_human_accounts_login CHECK (login ~ '^[a-z][a-z0-9._-]{2,63}$'),
            CONSTRAINT ck_human_accounts_role CHECK (role IN ('analyst','admin')),
            CONSTRAINT ck_human_accounts_admin_scope CHECK
                (role <> 'admin' OR cardinality(customer_ids)=0),
            CONSTRAINT ck_human_accounts_authorization_version CHECK
                (authorization_version > 0)
        );
        CREATE TABLE human_sessions (
            family_id uuid CONSTRAINT pk_human_sessions PRIMARY KEY,
            account_id uuid NOT NULL REFERENCES human_accounts(account_id),
            authorization_version integer NOT NULL,
            created_at timestamptz NOT NULL, rotated_at timestamptz NOT NULL,
            access_expires_at timestamptz NOT NULL, idle_expires_at timestamptz NOT NULL,
            absolute_expires_at timestamptz NOT NULL, generation integer NOT NULL,
            revoked_at timestamptz,
            access_sha256 varchar(64) NOT NULL
                CONSTRAINT uq_human_sessions_access_sha256 UNIQUE,
            refresh_sha256 varchar(64) NOT NULL
                CONSTRAINT uq_human_sessions_refresh_sha256 UNIQUE,
            csrf_sha256 varchar(64) NOT NULL,
            CONSTRAINT ck_human_sessions_versions CHECK
                (generation > 0 AND authorization_version > 0),
            CONSTRAINT ck_human_sessions_digests CHECK
                (length(access_sha256)=64 AND length(refresh_sha256)=64 AND length(csrf_sha256)=64)
        );
        CREATE INDEX ix_human_sessions_account_id ON human_sessions(account_id);
        CREATE INDEX ix_human_sessions_refresh ON human_sessions(refresh_sha256);
        CREATE TABLE human_consumed_refresh (
            refresh_sha256 varchar(64) CONSTRAINT pk_human_consumed_refresh PRIMARY KEY,
            family_id uuid NOT NULL REFERENCES human_sessions(family_id),
            csrf_sha256 varchar(64) NOT NULL, consumed_at timestamptz NOT NULL,
            expires_at timestamptz NOT NULL
        );
        CREATE INDEX ix_human_consumed_refresh_family_id ON human_consumed_refresh(family_id);
        CREATE INDEX ix_human_consumed_refresh_expires ON human_consumed_refresh(expires_at);
        CREATE TABLE human_login_throttle (
            bucket varchar(12) CONSTRAINT pk_human_login_throttle PRIMARY KEY,
            window_started_at timestamptz NOT NULL, attempts integer NOT NULL,
            CONSTRAINT ck_human_login_throttle_attempts CHECK (attempts >= 0)
        );
    """)
    op.execute("""
        CREATE FUNCTION fraudlens_prune_expired_refresh() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.expires_at > clock_timestamp() THEN
                RAISE EXCEPTION 'unexpired consumed refresh is immutable' USING ERRCODE='23514';
            END IF;
            RETURN OLD;
        END $$;
        CREATE TRIGGER human_consumed_refresh_expired_delete
            BEFORE DELETE ON human_consumed_refresh FOR EACH ROW
            EXECUTE FUNCTION fraudlens_prune_expired_refresh();
    """)
    for table in ("human_consumed_refresh",):
        for operation in ("UPDATE", "TRUNCATE"):
            level = "STATEMENT" if operation == "TRUNCATE" else "ROW"
            op.execute(
                f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} ON {table} "
                f"FOR EACH {level} EXECUTE FUNCTION fraudlens_reject_history_change()"
            )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS fraudlens_prune_expired_refresh() CASCADE")
    op.drop_table("human_login_throttle")
    op.drop_table("human_consumed_refresh")
    op.drop_table("human_sessions")
    op.drop_table("human_accounts")
