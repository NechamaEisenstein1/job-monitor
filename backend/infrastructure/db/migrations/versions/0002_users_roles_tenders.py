"""evaluation facets (role type, government tender, rank) + users, sessions, recruiters,
alerts, outreach, analytics

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("job_evaluations") as batch:
        batch.add_column(sa.Column("is_junior", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("location_matched", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("role_type", sa.String(32), nullable=False, server_default="other"))
        batch.add_column(sa.Column("is_government_tender", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("rank_score", sa.Float(), nullable=False, server_default="0"))

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(300), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("experience_level", sa.String(16), nullable=False, server_default="junior"),
        sa.Column("alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime()),
    )
    op.create_table(
        "user_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    op.create_table(
        "user_recruiters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("company", sa.String(300), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "email", name="uq_user_recruiters_user_email"),
    )
    op.create_index("ix_user_recruiters_user_id", "user_recruiters", ["user_id"])

    op.create_table(
        "user_job_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("scrape_run_id", sa.String(36)),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "job_id", name="uq_user_job_alerts"),
    )
    op.create_index("ix_user_job_alerts_user_id", "user_job_alerts", ["user_id"])

    op.create_table(
        "outreach_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("recruiter_id", sa.Integer(), sa.ForeignKey("user_recruiters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "job_id", "recruiter_id", name="uq_outreach_messages"),
    )
    op.create_index("ix_outreach_messages_user_id", "outreach_messages", ["user_id"])
    op.create_index("ix_outreach_messages_created_at", "outreach_messages", ["created_at"])

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("path", sa.String(200)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"])
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"])


def downgrade() -> None:
    for table in ("analytics_events", "outreach_messages", "user_job_alerts", "user_recruiters",
                  "user_sessions", "users"):
        op.drop_table(table)
    with op.batch_alter_table("job_evaluations") as batch:
        for column in ("rank_score", "is_government_tender", "role_type", "location_matched", "is_junior"):
            batch.drop_column(column)
