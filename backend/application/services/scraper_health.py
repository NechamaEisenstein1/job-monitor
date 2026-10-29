"""After each run: which sites' scrapers need a person, and one email about them.

The email goes out only when some site has just crossed its alert point (or is due for a
periodic reminder), and then lists every site that currently has a problem, so one message
gives the whole picture. Sent at most once per scheduled date."""
from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta

from backend.application.ports import NotificationRepository, ScraperRunRepository
from backend.config.settings import HealthConfig
from backend.domain.services.scraper_health import SiteHealth, assess
from backend.infrastructure.email.renderer import render_scraper_health
from backend.infrastructure.email.senders import EmailSender
from backend.observability import log_event

NOTIFICATION_TYPE = "scraper_health"


class ScraperHealthMonitor:
    def __init__(self, runs: ScraperRunRepository, notifications: NotificationRepository, sender: EmailSender,
                 recipient: str, cfg: HealthConfig, clock: Callable[[], datetime], base_url: str = "",
                 claim_timeout_minutes: int = 30):
        self._runs = runs
        self._notifications = notifications
        self._sender = sender
        self._recipient = recipient.strip()
        self._cfg = cfg
        self._clock = clock
        self._base_url = base_url
        self._claim_timeout = timedelta(minutes=claim_timeout_minutes)

    def report(self, sites: Sequence[str]) -> list[SiteHealth]:
        """Every site with a problem right now: failing, or working only through its fallback."""
        health = []
        for site in sites:
            current = assess(site, self._runs.recent_for_site(site, self._cfg.history_runs))
            if current is not None:
                health.append(current)
        return health

    def check(self, sites: Sequence[str], scheduled_date: date, run_id: str | None = None) -> list[SiteHealth]:
        """Logs every problem, emails when one is due. Returns the sites that were due."""
        unhealthy = self.report(sites)
        due = [h for h in unhealthy if h.due_for_alert(self._cfg.alert_after_failures, self._cfg.remind_every_runs)]
        for h in unhealthy:
            log_event("scraper_health", logging.WARNING, site=h.site, kind=h.kind.value, streak=h.streak,
                      degraded=h.degraded, alert_due=h in due)
        if not due:
            return due
        if not self._recipient:
            log_event("health_email_skipped", reason="no_recipient_configured")
            return due

        now = self._clock()
        if not self._notifications.try_claim(NOTIFICATION_TYPE, scheduled_date, self._recipient, run_id,
                                             now, now - self._claim_timeout):
            log_event("health_email_skipped", reason="already_sent", scheduled_date=scheduled_date)
            return due
        # Sites that just became due first, then the rest of the current problems; broken
        # sites before ones still collected through a fallback.
        ordered = sorted(unhealthy, key=lambda h: (h not in due, h.degraded, -h.streak, h.site))
        try:
            self._sender.send(self._recipient, render_scraper_health(ordered, scheduled_date, self._base_url))
        except Exception as exc:  # noqa: BLE001 - a failed send must release the claim
            self._notifications.release(NOTIFICATION_TYPE, scheduled_date, self._recipient)
            log_event("health_email_failed", logging.ERROR, error=type(exc).__name__)
            return due
        self._notifications.mark_sent(NOTIFICATION_TYPE, scheduled_date, self._recipient, self._clock())
        log_event("health_email_sent", sites=len(ordered), due=len(due))
        return due
