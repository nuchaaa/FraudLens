"""Bind additional-factor ceremonies to a current browser session."""

from alembic import op

revision = "0010_factor_lifecycle"
down_revision = "0009_human_webauthn"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE human_mfa_challenges
            ADD COLUMN session_family_id uuid REFERENCES human_sessions(family_id);
        ALTER TABLE human_mfa_challenges
            DROP CONSTRAINT ck_human_mfa_challenges_ceremony;
        ALTER TABLE human_mfa_challenges
            ADD CONSTRAINT ck_human_mfa_challenges_ceremony CHECK (
                ceremony IN ('LOGIN', 'FIRST_ENROLLMENT',
                             'ADD_FACTOR_PROOF', 'ADD_FACTOR_REGISTER')
                AND (ceremony NOT IN ('ADD_FACTOR_PROOF', 'ADD_FACTOR_REGISTER')
                     OR session_family_id IS NOT NULL)
            );
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE human_mfa_challenges
            DROP CONSTRAINT ck_human_mfa_challenges_ceremony;
        ALTER TABLE human_mfa_challenges
            ADD CONSTRAINT ck_human_mfa_challenges_ceremony CHECK (
                ceremony IN ('LOGIN', 'FIRST_ENROLLMENT')
            );
        ALTER TABLE human_mfa_challenges DROP COLUMN session_family_id;
    """)
