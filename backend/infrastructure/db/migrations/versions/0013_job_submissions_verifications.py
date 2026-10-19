"""job submissions by any user (admin approves them) and users' "details are correct" votes

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Where a user-submitted posting came from; shown on the job once it is approved.
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("source_recruiter", sa.String(200)))
        batch.add_column(sa.Column("source_published_on", sa.Date()))

    # A posting by a user without the recruiter role waits here until an admin approves it;
    # only then does it become a row in jobs (so nothing pending can leak onto the board).
    op.create_table(
        "job_submissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("submitted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirements", sa.Text(), nullable=False, server_default=""),
        sa.Column("tender_number", sa.String(100)),
        sa.Column("government_ministry", sa.String(200)),
        sa.Column("location", sa.String(200)),
        sa.Column("source_recruiter", sa.String(200), nullable=False),
        sa.Column("source_published_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.Column("review_note", sa.Text()),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="SET NULL")),
    )
    op.create_index("ix_job_submissions_status_created", "job_submissions", ["status", "created_at"])
    op.create_index("ix_job_submissions_user_created", "job_submissions", ["submitted_by", "created_at"])

    op.create_table(
        "job_verifications",
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_job_verifications_user_id", "job_verifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_job_verifications_user_id", table_name="job_verifications")
    op.drop_table("job_verifications")
    op.drop_index("ix_job_submissions_user_created", table_name="job_submissions")
    op.drop_index("ix_job_submissions_status_created", table_name="job_submissions")
    op.drop_table("job_submissions")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("source_published_on")
        batch.drop_column("source_recruiter")
