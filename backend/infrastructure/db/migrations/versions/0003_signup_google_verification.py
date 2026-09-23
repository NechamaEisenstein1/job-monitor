"""self sign-up, Google sign-in, email verification

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        # Google-only accounts have no password.
        batch.alter_column("password_hash", existing_type=sa.String(300), nullable=True)
        batch.add_column(sa.Column("google_sub", sa.String(64)))
        # Accounts that existed before self sign-up were created by an admin: trusted.
        batch.add_column(sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.create_unique_constraint("uq_users_google_sub", ["google_sub"])
    # From now on new rows must state verification explicitly.
    with op.batch_alter_table("users") as batch:
        batch.alter_column("email_verified", existing_type=sa.Boolean(), server_default=sa.false())

    op.create_table(
        "email_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_email_tokens_user_id", "email_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_table("email_tokens")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_google_sub", type_="unique")
        batch.drop_column("email_verified")
        batch.drop_column("google_sub")
        batch.alter_column("password_hash", existing_type=sa.String(300), nullable=False)
