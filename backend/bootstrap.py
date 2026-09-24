"""Composition root: the only place that wires infrastructure into use cases."""
from __future__ import annotations

import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import httpx
import truststore
from sqlalchemy.orm import Session

from backend.application.services.notification import NotificationService
from backend.application.services.scraper_executor import ScraperExecutor
from backend.application.use_cases.accounts import AccountService, EmailVerificationService, RecruiterService
from backend.application.use_cases.outreach import OutreachService
from backend.application.use_cases.run_pipeline import RunPipeline
from backend.application.use_cases.recruiting import BillingService, ManualJobService
from backend.application.use_cases.user_alerts import UserAlertService
from backend.config.settings import MatchingConfig, Settings, load_matching_config, load_sources_config
from backend.domain.services.evaluation import JobEvaluationService
from backend.infrastructure.repositories.billing import SqlBillingRepository
from backend.infrastructure.db.session import make_engine, make_session_factory
from backend.infrastructure.email.senders import EmailSender, FileEmailSender, SmtpEmailSender
from backend.infrastructure.repositories.sql import (
    SqlJobEvaluationRepository, SqlJobRepository, SqlJobSourceRepository, SqlNotificationRepository,
    SqlUnitOfWork,
)
from backend.infrastructure.repositories.users import (
    SqlAlertRepository, SqlAnalyticsRepository, SqlEmailTokenRepository, SqlOutreachRepository,
    SqlRecruiterRepository, SqlSessionRepository, SqlUserRepository,
)
from backend.infrastructure.oauth.google import GoogleOAuth
from backend.infrastructure.scrapers.http import RetryingHttpClient, RetryPolicy
from backend.infrastructure.scrapers.registry import build_scrapers


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_today(cfg: MatchingConfig) -> date:
    """The run's scheduled date is the calendar date in the configured timezone (Israel)."""
    return datetime.now(ZoneInfo(cfg.schedule.timezone)).date()


def build_email_sender(settings: Settings) -> EmailSender:
    if settings.smtp:
        return SmtpEmailSender(settings.smtp)
    return FileEmailSender(settings.email_outbox_dir)


USER_AGENT = "Mozilla/5.0 (compatible; JobMonitor/3.1; personal job-alert tool)"


@asynccontextmanager
async def http_client(cfg: MatchingConfig) -> AsyncIterator[RetryingHttpClient]:
    # Verify TLS with the OS trust store: works behind TLS-inspecting filters
    # (e.g. NetFree) whose root CA is installed in Windows, and is standard on Linux.
    async with httpx.AsyncClient(
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        timeout=cfg.scraper.timeout_seconds, follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "he-IL,he;q=0.9,en;q=0.8"},
    ) as client:
        yield RetryingHttpClient(
            client,
            RetryPolicy(cfg.scraper.max_retries, cfg.scraper.retry_backoff_seconds),
            rate_limit_per_site=cfg.scraper.rate_limit_per_site,
        )


def user_alert_service(session: Session, settings: Settings, cfg: MatchingConfig,
                       sender: EmailSender) -> UserAlertService:
    return UserAlertService(
        users=SqlUserRepository(session), recruiters=SqlRecruiterRepository(session),
        alerts=SqlAlertRepository(session), evaluations=SqlJobEvaluationRepository(session),
        jobs=SqlJobRepository(session), sources=SqlJobSourceRepository(session), sender=sender,
        config=cfg, base_url=settings.public_base_url, clock=utcnow,
    )


def account_service(session: Session, cfg: MatchingConfig) -> AccountService:
    return AccountService(SqlUserRepository(session), SqlSessionRepository(session),
                          SqlAnalyticsRepository(session), utcnow, cfg.users.session_days,
                          admin_emails=cfg.users.admin_email_set)


def manual_job_service(session: Session, cfg: MatchingConfig) -> ManualJobService:
    return ManualJobService(
        jobs=SqlJobRepository(session), evaluations=SqlJobEvaluationRepository(session),
        billing=SqlBillingRepository(session), evaluator=JobEvaluationService.from_config(cfg),
        cfg=cfg.billing, clock=utcnow,
    )


def billing_service(session: Session, cfg: MatchingConfig) -> BillingService:
    return BillingService(billing=SqlBillingRepository(session), cfg=cfg.billing, clock=utcnow)


def recruiter_service(session: Session) -> RecruiterService:
    return RecruiterService(SqlRecruiterRepository(session), utcnow)


def outreach_service(session: Session, settings: Settings, cfg: MatchingConfig,
                     sender: EmailSender) -> OutreachService:
    return OutreachService(
        recruiters=SqlRecruiterRepository(session), outreach=SqlOutreachRepository(session),
        jobs=SqlJobRepository(session), sources=SqlJobSourceRepository(session),
        evaluations=SqlJobEvaluationRepository(session), sender=sender,
        daily_limit=cfg.users.outreach_daily_limit, base_url=settings.public_base_url, clock=utcnow,
    )


@asynccontextmanager
async def pipeline_from_settings(settings: Settings) -> AsyncIterator[RunPipeline]:
    cfg = load_matching_config(settings.config_dir)
    sources = load_sources_config(settings.config_dir)
    session_factory = make_session_factory(make_engine(settings.database_url))
    sender = build_email_sender(settings)

    async with http_client(cfg) as http:
        with session_factory() as session, session_factory() as notification_session, \
                session_factory() as alerts_session:
            yield RunPipeline(
                uow=SqlUnitOfWork(session),
                scrapers=build_scrapers(sources, http),
                executor=ScraperExecutor(cfg.scraper.max_concurrent_workers, utcnow),
                config=cfg,
                evaluator=JobEvaluationService.from_config(cfg),
                notifications=NotificationService(
                    SqlNotificationRepository(notification_session), sender, cfg.email, utcnow,
                ),
                clock=utcnow,
                user_alerts=user_alert_service(alerts_session, settings, cfg, sender),
            )


def verification_service(session: Session, settings: Settings, sender: EmailSender) -> EmailVerificationService:
    admins = load_matching_config(settings.config_dir).users.admin_email_set
    return EmailVerificationService(SqlUserRepository(session), SqlEmailTokenRepository(session), sender,
                                    settings.public_base_url, utcnow, admin_emails=admins)


def google_oauth(settings: Settings) -> GoogleOAuth | None:
    if not settings.google_enabled:
        return None
    return GoogleOAuth(settings.google_client_id, settings.google_client_secret,
                       f"{settings.public_base_url.rstrip('/')}/api/auth/google/callback")
