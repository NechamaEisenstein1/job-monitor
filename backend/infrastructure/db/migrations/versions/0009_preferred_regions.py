"""preferred regions: per job evaluation (which regions a job is in) and per user

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Filled by the next scrape run, which re-evaluates every listed job and every manual posting.
    with op.batch_alter_table("job_evaluations") as batch:
        batch.add_column(sa.Column("regions", sa.String(200), nullable=False, server_default=""))
    # "" = all of Israel; each user picks their regions in the personal area.
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("preferred_regions", sa.String(200), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("preferred_regions")
    with op.batch_alter_table("job_evaluations") as batch:
        batch.drop_column("regions")
