"""recruiter role, manual postings, points ledger, subscriptions

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users.is_admin (bool) -> users.role (user | recruiter | admin), keeping every admin.
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("role", sa.String(16), nullable=False, server_default="user"))
        batch.add_column(sa.Column("points_balance", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("subscription_status", sa.String(16), nullable=False,
                                   server_default="inactive"))
    op.execute(sa.text("UPDATE users SET role = 'admin' WHERE is_admin"))
    with op.batch_alter_table("users") as batch:
        batch.drop_column("is_admin")

    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("posted_by", sa.Integer()))
        batch.add_column(sa.Column("tender_number", sa.String(100)))
        batch.add_column(sa.Column("government_ministry", sa.String(200)))
        batch.add_column(sa.Column("featured_until", sa.DateTime()))
        batch.create_foreign_key("fk_jobs_posted_by_users", "users", ["posted_by"], ["id"], ondelete="SET NULL")
        batch.create_unique_constraint("uq_jobs_tender_number", ["tender_number"])
        batch.create_index("ix_jobs_posted_by", ["posted_by"])

    # Manual postings are evaluated when published, outside any scrape run.
    with op.batch_alter_table("job_evaluations") as batch:
        batch.alter_column("scrape_run_id", existing_type=sa.String(36), nullable=True)

    op.create_table(
        "point_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("reference", sa.String(64)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_point_transactions_user_id", "point_transactions", ["user_id"])
    op.create_index("ix_point_transactions_created_at", "point_transactions", ["created_at"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("amount_paid", sa.Float(), nullable=False, server_default="0"),
        sa.Column("points_spent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payment_method", sa.String(16), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_expires_at", "subscriptions", ["expires_at"])


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_table("point_transactions")
    # Manual postings cannot exist without their columns.
    op.execute(sa.text("DELETE FROM job_evaluations WHERE scrape_run_id IS NULL"))
    with op.batch_alter_table("job_evaluations") as batch:
        batch.alter_column("scrape_run_id", existing_type=sa.String(36), nullable=False)
    op.execute(sa.text("DELETE FROM user_job_alerts WHERE job_id IN (SELECT id FROM jobs WHERE is_manual)"))
    op.execute(sa.text("DELETE FROM outreach_messages WHERE job_id IN (SELECT id FROM jobs WHERE is_manual)"))
    op.execute(sa.text("DELETE FROM jobs WHERE is_manual"))
    with op.batch_alter_table("jobs") as batch:
        batch.drop_index("ix_jobs_posted_by")
        batch.drop_constraint("uq_jobs_tender_number", type_="unique")
        batch.drop_constraint("fk_jobs_posted_by_users", type_="foreignkey")
        for column in ("featured_until", "government_ministry", "tender_number", "posted_by", "is_manual"):
            batch.drop_column(column)

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute(sa.text("UPDATE users SET is_admin = (role = 'admin')"))
    with op.batch_alter_table("users") as batch:
        batch.drop_column("subscription_status")
        batch.drop_column("points_balance")
        batch.drop_column("role")
