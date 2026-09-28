"""Bind removal target and prune expired raw WebAuthn challenges safely."""

from alembic import op

revision = "0011_factor_removal_retention"
down_revision = "0010_factor_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE human_mfa_challenges
            ADD COLUMN target_credential_id bytea
            REFERENCES human_authenticators(credential_id);
        CREATE INDEX ix_human_mfa_challenges_expires
            ON human_mfa_challenges(expires_at, challenge_id);
        ALTER TABLE human_mfa_challenges
            DROP CONSTRAINT ck_human_mfa_challenges_ceremony;
        ALTER TABLE human_mfa_challenges
            ADD CONSTRAINT ck_human_mfa_challenges_ceremony CHECK (
                ceremony IN ('LOGIN', 'FIRST_ENROLLMENT',
                             'ADD_FACTOR_PROOF', 'ADD_FACTOR_REGISTER',
                             'REMOVE_FACTOR_PROOF')
                AND (ceremony NOT IN ('ADD_FACTOR_PROOF', 'ADD_FACTOR_REGISTER',
                                     'REMOVE_FACTOR_PROOF')
                     OR session_family_id IS NOT NULL)
                AND ((ceremony = 'REMOVE_FACTOR_PROOF') =
                     (target_credential_id IS NOT NULL))
            );
        DROP TRIGGER human_mfa_challenges_no_delete ON human_mfa_challenges;
        CREATE FUNCTION fraudlens_prunable_mfa_challenge()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.expires_at >= statement_timestamp() - INTERVAL '1 day' THEN
                RAISE EXCEPTION 'challenge retention interval has not elapsed'
                    USING ERRCODE='23514';
            END IF;
            RETURN OLD;
        END $$;
        CREATE TRIGGER human_mfa_challenges_expired_delete
            BEFORE DELETE ON human_mfa_challenges
            FOR EACH ROW EXECUTE FUNCTION fraudlens_prunable_mfa_challenge();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER human_mfa_challenges_expired_delete ON human_mfa_challenges;
        DROP FUNCTION fraudlens_prunable_mfa_challenge();
        CREATE TRIGGER human_mfa_challenges_no_delete
            BEFORE DELETE ON human_mfa_challenges
            FOR EACH ROW EXECUTE FUNCTION fraudlens_reject_history_change();
        DROP INDEX ix_human_mfa_challenges_expires;
        ALTER TABLE human_mfa_challenges
            DROP CONSTRAINT ck_human_mfa_challenges_ceremony;
        ALTER TABLE human_mfa_challenges
            ADD CONSTRAINT ck_human_mfa_challenges_ceremony CHECK (
                ceremony IN ('LOGIN', 'FIRST_ENROLLMENT',
                             'ADD_FACTOR_PROOF', 'ADD_FACTOR_REGISTER')
                AND (ceremony NOT IN ('ADD_FACTOR_PROOF', 'ADD_FACTOR_REGISTER')
                     OR session_family_id IS NOT NULL)
            );
        ALTER TABLE human_mfa_challenges DROP COLUMN target_credential_id;
    """)
