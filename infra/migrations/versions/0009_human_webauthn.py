"""Local WebAuthn factors and one-use challenges; production login remains gated."""

from alembic import op

revision = "0009_human_webauthn"
down_revision = "0008_human_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE human_authenticators (
            credential_id bytea CONSTRAINT pk_human_authenticators PRIMARY KEY,
            account_id uuid NOT NULL REFERENCES human_accounts(account_id),
            public_key bytea NOT NULL,
            sign_count bigint NOT NULL,
            device_type varchar(30) NOT NULL,
            backed_up boolean NOT NULL,
            created_at timestamptz NOT NULL,
            last_used_at timestamptz,
            revoked_at timestamptz,
            CONSTRAINT ck_human_authenticators_material CHECK
                (octet_length(credential_id) BETWEEN 1 AND 1024
                 AND octet_length(public_key) BETWEEN 1 AND 4096),
            CONSTRAINT ck_human_authenticators_sign_count CHECK (sign_count >= 0),
            CONSTRAINT ck_human_authenticators_chronology CHECK
                ((last_used_at IS NULL OR last_used_at >= created_at)
                 AND (revoked_at IS NULL OR revoked_at >= created_at))
        );
        CREATE INDEX ix_human_authenticators_account_id
            ON human_authenticators(account_id);
        CREATE TABLE human_mfa_challenges (
            challenge_id uuid CONSTRAINT pk_human_mfa_challenges PRIMARY KEY,
            account_id uuid NOT NULL REFERENCES human_accounts(account_id),
            ceremony varchar(25) NOT NULL,
            challenge bytea NOT NULL CONSTRAINT uq_human_mfa_challenges_challenge UNIQUE,
            rp_id varchar(253) NOT NULL,
            origin varchar(300) NOT NULL,
            authorization_version integer NOT NULL,
            created_at timestamptz NOT NULL,
            expires_at timestamptz NOT NULL,
            consumed_at timestamptz,
            CONSTRAINT ck_human_mfa_challenges_ceremony CHECK
                (ceremony IN ('LOGIN', 'FIRST_ENROLLMENT')),
            CONSTRAINT ck_human_mfa_challenges_challenge_length CHECK
                (octet_length(challenge) = 32),
            CONSTRAINT ck_human_mfa_challenges_chronology CHECK
                (authorization_version > 0 AND expires_at > created_at
                 AND (consumed_at IS NULL OR consumed_at >= created_at))
        );
        CREATE INDEX ix_human_mfa_challenges_account_id
            ON human_mfa_challenges(account_id);
    """)
    op.execute("""
        CREATE FUNCTION fraudlens_guard_human_authenticator()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.credential_id <> OLD.credential_id
               OR NEW.account_id <> OLD.account_id
               OR NEW.public_key <> OLD.public_key
               OR NEW.created_at <> OLD.created_at
               OR NEW.device_type <> OLD.device_type
               OR NEW.backed_up <> OLD.backed_up
               OR NEW.sign_count < OLD.sign_count
               OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at)
               OR (OLD.last_used_at IS NOT NULL AND
                   (NEW.last_used_at IS NULL OR NEW.last_used_at < OLD.last_used_at))
            THEN
                RAISE EXCEPTION 'authenticator history is immutable' USING ERRCODE='23514';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER human_authenticators_guard BEFORE UPDATE ON human_authenticators
            FOR EACH ROW EXECUTE FUNCTION fraudlens_guard_human_authenticator();
        CREATE FUNCTION fraudlens_guard_mfa_challenge()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF to_jsonb(NEW) - 'consumed_at' IS DISTINCT FROM
               to_jsonb(OLD) - 'consumed_at'
               OR OLD.consumed_at IS NOT NULL
               OR NEW.consumed_at IS NULL
            THEN
                RAISE EXCEPTION 'challenge history is immutable' USING ERRCODE='23514';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER human_mfa_challenges_guard BEFORE UPDATE ON human_mfa_challenges
            FOR EACH ROW EXECUTE FUNCTION fraudlens_guard_mfa_challenge();
    """)
    for table in ("human_authenticators", "human_mfa_challenges"):
        for operation in ("DELETE", "TRUNCATE"):
            level = "STATEMENT" if operation == "TRUNCATE" else "ROW"
            op.execute(
                f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} ON {table} "
                f"FOR EACH {level} EXECUTE FUNCTION fraudlens_reject_history_change()"
            )


def downgrade() -> None:
    op.drop_table("human_mfa_challenges")
    op.drop_table("human_authenticators")
    op.execute("DROP FUNCTION fraudlens_guard_mfa_challenge()")
    op.execute("DROP FUNCTION fraudlens_guard_human_authenticator()")
