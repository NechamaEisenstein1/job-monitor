"""send outreach from the user's Gmail + read tracking

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gmail_connections",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("google_email", sa.String(320), nullable=False),
        sa.Column("refresh_token_enc", sa.Text(), nullable=False),
        sa.Column("scopes", sa.String(500), nullable=False),
        sa.Column("connected_at", sa.DateTime(), nullable=False),
    )
    with op.batch_alter_table("outreach_messages") as batch:
        batch.add_column(sa.Column("sent_via", sa.String(16)))
        batch.add_column(sa.Column("tracking_token", sa.String(64)))
        batch.add_column(sa.Column("opened_at", sa.DateTime()))
        batch.add_column(sa.Column("last_opened_at", sa.DateTime()))
        batch.add_column(sa.Column("open_count", sa.Integer(), nullable=False, server_default="0"))
        batch.create_unique_constraint("uq_outreach_messages_tracking_token", ["tracking_token"])


def downgrade() -> None:
    with op.batch_alter_table("outreach_messages") as batch:
        batch.drop_constraint("uq_outreach_messages_tracking_token", type_="unique")
        for column in ("open_count", "last_opened_at", "opened_at", "tracking_token", "sent_via"):
            batch.drop_column(column)
    op.drop_table("gmail_connections")
