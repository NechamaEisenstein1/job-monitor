"""contact replies: the admin answers a message on the site; the user reads it in the personal area

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("contact_messages") as batch:
        batch.add_column(sa.Column("reply", sa.Text()))
        batch.add_column(sa.Column("replied_at", sa.DateTime()))
    op.create_index("ix_contact_messages_user_id", "contact_messages", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_contact_messages_user_id", table_name="contact_messages")
    with op.batch_alter_table("contact_messages") as batch:
        batch.drop_column("replied_at")
        batch.drop_column("reply")
