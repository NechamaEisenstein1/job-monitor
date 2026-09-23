"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-23
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("sites_total", sa.Integer(), nullable=False),
        sa.Column("sites_succeeded", sa.Integer(), nullable=False),
        sa.Column("sites_failed", sa.Integer(), nullable=False),
        sa.Column("raw_jobs_found", sa.Integer(), nullable=False),
        sa.Column("normalized_jobs", sa.Integer(), nullable=False),
        sa.Column("canonical_jobs_touched", sa.Integer(), nullable=False),
        sa.Column("eligible_jobs", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_scrape_runs_scheduled_date", "scrape_runs", ["scheduled_date"])

    op.create_table(
        "scraper_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("scrape_runs.id"), nullable=False),
        sa.Column("site", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("jobs_fetched", sa.Integer(), nullable=False),
        sa.Column("jobs_parsed", sa.Integer(), nullable=False),
        sa.Column("jobs_invalid", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("warning", sa.Text()),
    )
    op.create_index("ix_scraper_runs_run_id", "scraper_runs", ["run_id"])
    op.create_index("ix_scraper_runs_site_status_started", "scraper_runs", ["site", "status", "started_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirements", sa.Text(), nullable=False),
        sa.Column("client_company", sa.String(300)),
        sa.Column("employment_type", sa.String(100)),
        sa.Column("location", sa.String(200)),
        sa.Column("region", sa.String(200)),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),  # NOT unique
    )
    op.create_index("ix_jobs_last_seen_at", "jobs", ["last_seen_at"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "job_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("recruitment_company", sa.String(200), nullable=False),
        sa.Column("source_job_id", sa.String(200)),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_url_fingerprint", sa.String(64), nullable=False),
        sa.Column("external_title", sa.String(500)),
        sa.Column("source_metadata_hash", sa.String(64)),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("first_scrape_run_id", sa.String(36), sa.ForeignKey("scrape_runs.id"), nullable=False),
        sa.Column("last_scrape_run_id", sa.String(36), sa.ForeignKey("scrape_runs.id"), nullable=False),
    )
    op.create_index("ix_job_sources_job_id", "job_sources", ["job_id"])
    # Partial unique indexes: source identity.
    op.create_index(
        "uq_job_sources_company_source_job_id", "job_sources",
        ["recruitment_company", "source_job_id"], unique=True,
        postgresql_where=sa.text("source_job_id IS NOT NULL"),
        sqlite_where=sa.text("source_job_id IS NOT NULL"),
    )
    op.create_index(
        "uq_job_sources_company_url_fingerprint", "job_sources",
        ["recruitment_company", "source_url_fingerprint"], unique=True,
        postgresql_where=sa.text("source_job_id IS NULL"),
        sqlite_where=sa.text("source_job_id IS NULL"),
    )

    op.create_table(
        "job_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("scrape_run_id", sa.String(36), sa.ForeignKey("scrape_runs.id"), nullable=False),
        sa.Column("junior_score", sa.Float(), nullable=False),
        sa.Column("is_eligible", sa.Boolean(), nullable=False),
        sa.Column("matched_rules", sa.JSON(), nullable=False),
        sa.Column("rejection_reasons", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("job_id", "scrape_run_id", name="uq_job_evaluations_job_run"),
    )
    op.create_index("ix_job_evaluations_job_id", "job_evaluations", ["job_id"])
    op.create_index("ix_job_evaluations_scrape_run_id", "job_evaluations", ["scrape_run_id"])

    op.create_table(
        "job_changes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("job_source_id", sa.Integer(), sa.ForeignKey("job_sources.id"), nullable=False),
        sa.Column("scrape_run_id", sa.String(36), sa.ForeignKey("scrape_runs.id"), nullable=False),
        sa.Column("change_type", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_job_changes_job_id", "job_changes", ["job_id"])
    op.create_index("ix_job_changes_scrape_run_id", "job_changes", ["scrape_run_id"])
    op.create_index("ix_job_changes_created_at", "job_changes", ["created_at"])

    op.create_table(
        "sent_notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("notification_type", sa.String(64), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("recipient", sa.String(320), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("scrape_run_id", sa.String(36)),
        sa.Column("claimed_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime()),
        sa.UniqueConstraint("notification_type", "scheduled_date", "recipient", name="uq_sent_notifications_key"),
    )


def downgrade() -> None:
    for table in ("sent_notifications", "job_changes", "job_evaluations", "job_sources",
                  "jobs", "scraper_runs", "scrape_runs"):
        op.drop_table(table)
