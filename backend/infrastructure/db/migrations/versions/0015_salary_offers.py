"""salary offers members share anonymously, by level, to compare and negotiate

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "salary_offers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("submitted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("role_type", sa.String(32), nullable=False),
        sa.Column("agency", sa.String(80), nullable=False),
        sa.Column("client_type", sa.String(16), nullable=False),
        sa.Column("offered_month", sa.Date(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("base_salary", sa.Integer(), nullable=False),
        sa.Column("extras", sa.JSON(), nullable=False),
        sa.Column("hours_per_day", sa.Float(), nullable=False),
        sa.Column("vacation_days", sa.Integer(), nullable=False),
        sa.Column("sick_pay", sa.String(32), nullable=False),
        sa.Column("contribution_base", sa.String(16), nullable=False),
        sa.Column("contribution_percent", sa.Integer(), nullable=False),
        sa.Column("study_fund_start", sa.String(32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_salary_offers_status_level_month", "salary_offers", ["status", "level", "offered_month"])
    op.create_index("ix_salary_offers_submitted_by", "salary_offers", ["submitted_by"])


def downgrade() -> None:
    op.drop_index("ix_salary_offers_submitted_by", table_name="salary_offers")
    op.drop_index("ix_salary_offers_status_level_month", table_name="salary_offers")
    op.drop_table("salary_offers")
