"""experience levels A/B/C for users + jobs a user applied to

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # junior -> level A; experienced (every seniority until now) -> level B, the nearest level.
    op.execute("UPDATE users SET experience_level = 'a' WHERE experience_level = 'junior'")
    op.execute("UPDATE users SET experience_level = 'b' WHERE experience_level = 'experienced'")
    op.create_table(
        "job_applications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        # Kept (NULL) when the job is removed from the board; the snapshot below stays readable.
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("client_company", sa.String(300)),
        sa.Column("location", sa.String(300)),
        sa.Column("source_url", sa.Text()),
        sa.Column("applied_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "job_id", name="uq_job_applications_user_job"),
    )
    op.create_index("ix_job_applications_user_id", "job_applications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_job_applications_user_id", table_name="job_applications")
    op.drop_table("job_applications")
    op.execute("UPDATE users SET experience_level = 'junior' WHERE experience_level = 'a'")
    op.execute("UPDATE users SET experience_level = 'experienced' WHERE experience_level IN ('b', 'c')")
