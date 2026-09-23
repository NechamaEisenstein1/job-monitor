"""SQLAlchemy table mappings. Column names mirror the domain dataclass fields.
Schema is created by Alembic migrations only - never at app startup."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScrapeRunRow(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16))
    sites_total: Mapped[int] = mapped_column(Integer, default=0)
    sites_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    sites_failed: Mapped[int] = mapped_column(Integer, default=0)
    raw_jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    normalized_jobs: Mapped[int] = mapped_column(Integer, default=0)
    canonical_jobs_touched: Mapped[int] = mapped_column(Integer, default=0)
    eligible_jobs: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class ScraperRunRow(Base):
    __tablename__ = "scraper_runs"
    __table_args__ = (Index("ix_scraper_runs_site_status_started", "site", "status", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("scrape_runs.id"), index=True)
    site: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    jobs_fetched: Mapped[int] = mapped_column(Integer, default=0)
    jobs_parsed: Mapped[int] = mapped_column(Integer, default=0)
    jobs_invalid: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    warning: Mapped[str | None] = mapped_column(Text)


class JobRow(Base):
    __tablename__ = "jobs"
    # NOTE: deliberately no unique constraint on content_hash (it is not identity).

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[str] = mapped_column(Text, default="")
    client_company: Mapped[str | None] = mapped_column(String(300))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(200))
    region: Mapped[str | None] = mapped_column(String(200))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))


class JobSourceRow(Base):
    __tablename__ = "job_sources"
    __table_args__ = (
        Index(
            "uq_job_sources_company_source_job_id",
            "recruitment_company", "source_job_id",
            unique=True,
            postgresql_where=text("source_job_id IS NOT NULL"),
            sqlite_where=text("source_job_id IS NOT NULL"),
        ),
        Index(
            "uq_job_sources_company_url_fingerprint",
            "recruitment_company", "source_url_fingerprint",
            unique=True,
            postgresql_where=text("source_job_id IS NULL"),
            sqlite_where=text("source_job_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    recruitment_company: Mapped[str] = mapped_column(String(200))
    source_job_id: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(Text)
    source_url_fingerprint: Mapped[str] = mapped_column(String(64))
    external_title: Mapped[str | None] = mapped_column(String(500))
    source_metadata_hash: Mapped[str | None] = mapped_column(String(64))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32))
    first_scrape_run_id: Mapped[str] = mapped_column(ForeignKey("scrape_runs.id"))
    last_scrape_run_id: Mapped[str] = mapped_column(ForeignKey("scrape_runs.id"))


class JobEvaluationRow(Base):
    __tablename__ = "job_evaluations"
    __table_args__ = (UniqueConstraint("job_id", "scrape_run_id", name="uq_job_evaluations_job_run"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    scrape_run_id: Mapped[str] = mapped_column(ForeignKey("scrape_runs.id"), index=True)
    junior_score: Mapped[float] = mapped_column(Float)
    is_eligible: Mapped[bool] = mapped_column(Boolean)
    matched_rules: Mapped[list] = mapped_column(JSON, default=list)
    rejection_reasons: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    is_junior: Mapped[bool] = mapped_column(Boolean, default=False)
    location_matched: Mapped[bool] = mapped_column(Boolean, default=False)
    role_type: Mapped[str] = mapped_column(String(32), default="other")
    is_government_tender: Mapped[bool] = mapped_column(Boolean, default=False)
    rank_score: Mapped[float] = mapped_column(Float, default=0.0)


class JobChangeRow(Base):
    __tablename__ = "job_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    job_source_id: Mapped[int] = mapped_column(ForeignKey("job_sources.id"))
    scrape_run_id: Mapped[str] = mapped_column(ForeignKey("scrape_runs.id"), index=True)
    change_type: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class SentNotificationRow(Base):
    __tablename__ = "sent_notifications"
    __table_args__ = (
        UniqueConstraint("notification_type", "scheduled_date", "recipient", name="uq_sent_notifications_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notification_type: Mapped[str] = mapped_column(String(64))
    scheduled_date: Mapped[date] = mapped_column(Date)
    recipient: Mapped[str] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(16))  # pending | sent
    scrape_run_id: Mapped[str | None] = mapped_column(String(36))
    claimed_at: Mapped[datetime] = mapped_column(DateTime)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)


# ------------------------------------------------------------------ users (migration 0002)

class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(String(300))  # None = Google-only account
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    experience_level: Mapped[str] = mapped_column(String(16), default="junior")
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)


class EmailTokenRow(Base):
    """Single-use email links (verification). Only the SHA-256 of the token is stored."""
    __tablename__ = "email_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class UserSessionRow(Base):
    __tablename__ = "user_sessions"

    # SHA-256 of the cookie token; the raw token is never stored.
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class RecruiterRow(Base):
    __tablename__ = "user_recruiters"
    __table_args__ = (UniqueConstraint("user_id", "email", name="uq_user_recruiters_user_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320))
    company: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class UserJobAlertRow(Base):
    """One row per (user, job) already alerted - the per-user alert idempotency key."""
    __tablename__ = "user_job_alerts"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job_alerts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    scrape_run_id: Mapped[str | None] = mapped_column(String(36))
    sent_at: Mapped[datetime] = mapped_column(DateTime)


class OutreachMessageRow(Base):
    """One personalised email per (user, job, recruiter); the unique key prevents re-sending."""
    __tablename__ = "outreach_messages"
    __table_args__ = (UniqueConstraint("user_id", "job_id", "recruiter_id", name="uq_outreach_messages"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    recruiter_id: Mapped[int] = mapped_column(ForeignKey("user_recruiters.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class AnalyticsEventRow(Base):
    """Logins and page views for the admin dashboard. No IPs or user agents are kept."""
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)  # login | login_failed | page_view
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    path: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
