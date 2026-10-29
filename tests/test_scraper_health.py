"""Scraper health: failure kinds, streaks, when an alert is due, and the alert email."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta

import pytest

from backend.config.settings import HealthConfig
from backend.domain.enums import ScrapeStatus
from backend.domain.models import ScraperRun
from backend.domain.services.scraper_health import (
    FailureKind, assess, classify, fallback_kind, fallback_note,
)

T0 = datetime(2026, 10, 29, 4, 0)
OK, PARSE, TIMEOUT, NET = (ScrapeStatus.SUCCESS, ScrapeStatus.PARSE_ERROR, ScrapeStatus.TIMEOUT,
                           ScrapeStatus.NETWORK_ERROR)


def runs(site: str, *outcomes: tuple[ScrapeStatus, str | None, str | None]) -> list[ScraperRun]:
    """Newest first: outcomes[0] is today's run, outcomes[1] yesterday's..."""
    return [ScraperRun(id=i, run_id=f"r{i}", site=site, status=status, started_at=T0 - timedelta(days=i),
                       finished_at=T0 - timedelta(days=i), jobs_fetched=0, jobs_parsed=0, jobs_invalid=0,
                       error=error, warning=warning)
            for i, (status, error, warning) in enumerate(outcomes)]


def ok(warning: str | None = None):
    return (OK, None, warning)


def failed(status: ScrapeStatus = PARSE, error: str = "Site: list not found - site layout may have changed"):
    return (status, error, None)


FALLBACK = fallback_note(FailureKind.BLOCKED, "HTTP 403 for https://x (Cloudflare)", "JobNet")


@pytest.mark.parametrize("status, error, kind", [
    (OK, None, None),
    (ScrapeStatus.CONFIG_ERROR, "missing option", FailureKind.CONFIG),
    (PARSE, "layout may have changed", FailureKind.LAYOUT),
    (ScrapeStatus.ZERO_RESULTS, None, FailureKind.LAYOUT),
    (TIMEOUT, "timeout after 4 attempts: https://yaelgroup.com/jobs/", FailureKind.TEMPORARY),
    (NET, "HTTP 403 for https://gav.co.il/wp-json/wp/v2/areas (server=nginx)", FailureKind.BLOCKED),
    (NET, "HTTP 401 for https://x", FailureKind.BLOCKED),
    (NET, "HTTP 404 for https://x/jobs", FailureKind.GONE),
    (NET, "HTTP 503 for https://x", FailureKind.TEMPORARY),
    (NET, "ConnectError after 4 attempts: https://x", FailureKind.TEMPORARY),
])
def test_classify(status, error, kind):
    assert classify(status, error) == kind


def test_fallback_note_round_trips_its_kind():
    assert fallback_kind(FALLBACK) == FailureKind.BLOCKED
    assert fallback_kind("3 listing(s) could not be read; " + FALLBACK) == FailureKind.BLOCKED
    assert fallback_kind("scraper returned zero jobs") is None and fallback_kind(None) is None


def test_clean_success_is_healthy():
    assert assess("Ness", runs("Ness", ok(), failed())) is None
    assert assess("Ness", []) is None


def test_failure_streak_and_last_success():
    health = assess("Yael", runs("Yael", failed(TIMEOUT, "timeout"), failed(TIMEOUT, "timeout"), ok(), failed()))
    assert health.kind == FailureKind.TEMPORARY and health.streak == 2 and not health.degraded
    assert health.last_success_at == T0 - timedelta(days=2)


def test_working_through_fallback_is_degraded_not_failed():
    health = assess("GAV", runs("GAV", ok(FALLBACK), ok(FALLBACK), failed(NET, "HTTP 403 for https://x")))
    assert health.degraded and health.kind == FailureKind.BLOCKED and health.streak == 2
    assert health.last_success_at is None


@pytest.mark.parametrize("outcomes, due", [
    # temporary: only from the 3rd failure in a row, then every 7 runs
    ([failed(TIMEOUT, "t")] * 1, False),
    ([failed(TIMEOUT, "t")] * 2, False),
    ([failed(TIMEOUT, "t")] * 3, True),
    ([failed(TIMEOUT, "t")] * 4, False),
    ([failed(TIMEOUT, "t")] * 10, True),
    # blocked: same rule
    ([failed(NET, "HTTP 403 for x")] * 3, True),
    # layout / gone: on the first failure (they never heal by themselves), then reminders
    ([failed()], True),
    ([failed()] * 2, False),
    ([failed()] * 8, True),
    ([failed(NET, "HTTP 404 for x")], True),
    # fallback in use: reported on the first run
    ([ok(FALLBACK)], True),
    ([ok(FALLBACK)] * 2, False),
])
def test_due_for_alert(outcomes, due):
    health = assess("Site", runs("Site", *outcomes))
    assert health.due_for_alert(alert_after=3, remind_every=7) is due


# ---------------------------------------------------------------- monitor + email

class FakeRuns:
    def __init__(self, by_site: dict[str, list[ScraperRun]]):
        self.by_site = by_site

    def recent_for_site(self, site, limit):
        return self.by_site.get(site, [])[:limit]


class FakeClaims:
    def __init__(self):
        self.claimed: set[tuple] = set()

    def try_claim(self, kind, day, recipient, run_id, now, stale_before):
        key = (kind, day, recipient)
        if key in self.claimed:
            return False
        self.claimed.add(key)
        return True

    def mark_sent(self, *args):
        pass

    def release(self, kind, day, recipient):
        self.claimed.discard((kind, day, recipient))


class Sender:
    def __init__(self, fail: bool = False):
        self.sent, self.fail = [], fail

    def send(self, recipient, email):
        if self.fail:
            raise ConnectionError("smtp down")
        self.sent.append((recipient, email))


def monitor(by_site, sender, recipient="owner@example.com"):
    from backend.application.services.scraper_health import ScraperHealthMonitor
    claims = FakeClaims()
    return ScraperHealthMonitor(FakeRuns(by_site), claims, sender, recipient, HealthConfig(), lambda: T0,
                                base_url="https://jobs.example.com"), claims


def test_monitor_emails_once_with_every_current_problem():
    sender = Sender()
    by_site = {
        "ProLogic": runs("ProLogic", failed()),                                   # layout: due now
        "Yael": runs("Yael", failed(TIMEOUT, "t"), ok()),                        # temporary, 1 run: not due
        "GAV Systems": runs("GAV Systems", ok(FALLBACK)),                        # degraded: due now
        "Ness": runs("Ness", ok()),                                              # healthy
    }
    m, _ = monitor(by_site, sender)
    due = m.check(list(by_site), date(2026, 10, 29), "r0")
    assert {h.site for h in due} == {"ProLogic", "GAV Systems"}
    assert len(sender.sent) == 1
    recipient, email = sender.sent[0]
    assert recipient == "owner@example.com"
    assert "2 אתרים דורשים טיפול" in email.subject  # ProLogic + Yael; GAV still works via its board
    assert email.html.index("ProLogic") < email.html.index("GAV Systems") < email.html.index("Yael")
    assert "Ness" not in email.html and "https://jobs.example.com/sources" in email.html

    m.check(list(by_site), date(2026, 10, 29), "r0-again")   # same day: never twice
    assert len(sender.sent) == 1


def test_monitor_is_quiet_when_nothing_is_due():
    sender = Sender()
    m, _ = monitor({"Yael": runs("Yael", failed(TIMEOUT, "t"))}, sender)
    assert m.check(["Yael"], date(2026, 10, 29)) == [] and sender.sent == []


def test_monitor_releases_the_claim_when_sending_fails():
    by_site = {"ProLogic": runs("ProLogic", failed())}
    m, claims = monitor(by_site, Sender(fail=True))
    m.check(["ProLogic"], date(2026, 10, 29))
    assert not claims.claimed  # tomorrow's (or a retried) run may still send it


def test_monitor_without_recipient_only_logs():
    sender = Sender()
    m, _ = monitor({"ProLogic": runs("ProLogic", failed())}, sender, recipient="  ")
    assert len(m.check(["ProLogic"], date(2026, 10, 29))) == 1 and sender.sent == []


def test_executor_records_the_fallback_note_as_a_warning():
    from backend.application.services.scraper_executor import ScraperExecutor
    from backend.domain.models import RawJob
    from backend.infrastructure.scrapers.base import BaseScraper

    class OnFallback(BaseScraper):
        site_name = "GAV Systems"
        note = FALLBACK

        async def fetch_jobs(self):
            return [RawJob(recruitment_company="GAV Systems", source_job_id="1", source_url="https://x/1",
                           title="Dev", description="", requirements="", client_company=None,
                           employment_type=None, location=None, region=None, published_at=None)]

    result = asyncio.run(ScraperExecutor(1, lambda: T0).execute(OnFallback()))
    assert result.status == ScrapeStatus.SUCCESS and fallback_kind(result.warning) == FailureKind.BLOCKED
