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
    # migration 0004: recruiter postings
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    posted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    tender_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    government_ministry: Mapped[str | None] = mapped_column(String(200))
    featured_until: Mapped[datetime | None] = mapped_column(DateTime)


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
    scrape_run_id: Mapped[str | None] = mapped_column(ForeignKey("scrape_runs.id"), index=True)
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
    # migration 0005
    required_years: Mapped[float | None] = mapped_column(Float)
    junior_title_mismatch: Mapped[bool] = mapped_column(Boolean, default=False)


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
    role: Mapped[str] = mapped_column(String(16), default="user")  # user | recruiter | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    experience_level: Mapped[str] = mapped_column(String(16), default="junior")
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # Changed only through atomic UPDATEs in the billing repository.
    points_balance: Mapped[int] = mapped_column(Integer, default=0)
    subscription_status: Mapped[str] = mapped_column(String(16), default="inactive")


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
    # migration 0006: how it was sent, and read tracking (a 1x1 image in the email)
    sent_via: Mapped[str | None] = mapped_column(String(16))  # gmail | site
    tracking_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime)
    open_count: Mapped[int] = mapped_column(Integer, default=0)


class AnalyticsEventRow(Base):
    """Logins and page views for the admin dashboard. No IPs or user agents are kept."""
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)  # login | login_failed | page_view
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    path: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


# ------------------------------------------------------------------ billing (migration 0004)

class PointTransactionRow(Base):
    __tablename__ = "point_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    action_type: Mapped[str] = mapped_column(String(32))
    reference: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class SubscriptionRow(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16))
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    points_spent: Mapped[int] = mapped_column(Integer, default=0)
    payment_method: Mapped[str] = mapped_column(String(16))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


# ------------------------------------------------------------------ history (migration 0005)

class PostingHistoryRow(Base):
    """Outlives job_sources: removed postings keep their row so re-publications are seen."""
    __tablename__ = "posting_history"
    __table_args__ = (
        UniqueConstraint("recruitment_company", "posting_key", name="uq_posting_history_company_key"),
        Index("ix_posting_history_company_title", "recruitment_company", "title_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recruitment_company: Mapped[str] = mapped_column(String(200))
    posting_key: Mapped[str] = mapped_column(String(260))
    title_key: Mapped[str] = mapped_column(String(300))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime)
    origin_first_seen_at: Mapped[datetime] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime)
    gone_at: Mapped[datetime | None] = mapped_column(DateTime)
    reposts: Mapped[int] = mapped_column(Integer, default=0)


class GmailConnectionRow(Base):
    """A user's permission to send from their Gmail. Only an ENCRYPTED refresh token is kept."""
    __tablename__ = "gmail_connections"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    google_email: Mapped[str] = mapped_column(String(320))
    refresh_token_enc: Mapped[str] = mapped_column(Text)
    scopes: Mapped[str] = mapped_column(String(500))
    connected_at: Mapped[datetime] = mapped_column(DateTime)
