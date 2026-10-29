"""Scraper health: why a site failed, and whether a person needs to look at it.

Every failure is sorted into a kind that says what fixes it:

    temporary - timeouts, 429/5xx, dropped connections. Retried; usually heals by itself.
    blocked   - the site refuses automated requests (401/403, bot protection). A job-board
                fallback keeps the jobs flowing; nothing to fix in our code.
    layout    - the page structure the parser relies on is gone (parse error, a sudden zero).
                The parser has to be updated.
    gone      - the address no longer exists (404/410). The source URL has to be updated.
    config    - config/sources.yaml is wrong.

A site that succeeded only through its fallback board is "degraded": the jobs are there, but
its own scraper is broken and is reported once (then as a periodic reminder).

Alerting rule: kinds that never heal by themselves (layout, gone, config) are reported on the
first failure; temporary and blocked failures only after `alert_after` consecutive failed runs.
After that, a reminder every `remind_every` runs - never the same alert every day."""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from backend.domain.enums import ScrapeStatus
from backend.domain.models import ScraperRun

#: Prefix of the run warning a fallback scraper leaves when it had to use its board.
FALLBACK_PREFIX = "fallback used"

_HTTP_STATUS = re.compile(r"\bHTTP (\d{3})\b")
_FALLBACK_KIND = re.compile(re.escape(FALLBACK_PREFIX) + r" \((\w+)\)")


class FailureKind(Enum):
    TEMPORARY = "temporary"
    BLOCKED = "blocked"
    LAYOUT = "layout"
    GONE = "gone"
    CONFIG = "config"


#: Kinds that will not fix themselves: reported on the first occurrence.
IMMEDIATE = frozenset({FailureKind.LAYOUT, FailureKind.GONE, FailureKind.CONFIG})


def classify(status: ScrapeStatus, error: str | None = None) -> FailureKind | None:
    """The kind of a scraper outcome; None for a success."""
    if status == ScrapeStatus.SUCCESS:
        return None
    if status == ScrapeStatus.CONFIG_ERROR:
        return FailureKind.CONFIG
    if status in (ScrapeStatus.PARSE_ERROR, ScrapeStatus.ZERO_RESULTS):
        return FailureKind.LAYOUT
    if status == ScrapeStatus.TIMEOUT:
        return FailureKind.TEMPORARY
    match = _HTTP_STATUS.search(error or "")
    if match:
        code = int(match.group(1))
        if code in (401, 403, 451):
            return FailureKind.BLOCKED
        if code in (404, 410):
            return FailureKind.GONE
    return FailureKind.TEMPORARY


def fallback_note(kind: FailureKind, error: str, board: str) -> str:
    """The run warning recorded when a site's own scraper failed and its board was used."""
    return f"{FALLBACK_PREFIX} ({kind.value}): own site failed - {error[:200]}; jobs collected from {board}"


def fallback_kind(warning: str | None) -> FailureKind | None:
    """The kind of own-site failure recorded in a fallback warning, if the run used one."""
    match = _FALLBACK_KIND.search(warning or "")
    if not match:
        return None
    try:
        return FailureKind(match.group(1))
    except ValueError:
        return FailureKind.TEMPORARY


@dataclass(frozen=True)
class SiteHealth:
    site: str
    kind: FailureKind
    #: Consecutive runs (newest first) that failed - or, when degraded, that needed the fallback.
    streak: int
    degraded: bool          # jobs still collected, through the fallback board
    last_error: str | None
    last_success_at: datetime | None   # last run whose own scraper worked

    def due_for_alert(self, alert_after: int, remind_every: int) -> bool:
        start = 1 if (self.degraded or self.kind in IMMEDIATE) else max(1, alert_after)
        if self.streak < start:
            return False
        return self.streak == start or (remind_every > 0 and (self.streak - start) % remind_every == 0)


def assess(site: str, runs: Sequence[ScraperRun]) -> SiteHealth | None:
    """Health of one site from its recent runs, newest first. None when the latest run was a
    clean success (or there are no runs)."""
    if not runs:
        return None
    latest = runs[0]
    latest_fallback = fallback_kind(latest.warning) if latest.status == ScrapeStatus.SUCCESS else None
    if latest.status == ScrapeStatus.SUCCESS and latest_fallback is None:
        return None

    degraded = latest_fallback is not None
    streak = 0
    for run in runs:
        failed = run.status != ScrapeStatus.SUCCESS
        on_fallback = run.status == ScrapeStatus.SUCCESS and fallback_kind(run.warning) is not None
        if (degraded and on_fallback) or (not degraded and failed):
            streak += 1
        else:
            break

    last_clean = next((r for r in runs if r.status == ScrapeStatus.SUCCESS and fallback_kind(r.warning) is None),
                      None)
    if degraded:
        kind, error = latest_fallback, latest.warning
    else:
        kind, error = classify(latest.status, latest.error), latest.error
    return SiteHealth(site=site, kind=kind, streak=streak, degraded=degraded, last_error=error,
                      last_success_at=last_clean.started_at if last_clean else None)


#: What each kind means and what to do about it (shown in the alert email).
ADVICE = {
    FailureKind.TEMPORARY: "תקלה זמנית באתר (איטיות או עומס). המערכת מנסה שוב בכל ריצה. אם זה נמשך, ייתכן שהאתר מאט בכוונה בקשות אוטומטיות - כדאי להגדיר לו מקור גיבוי.",
    FailureKind.BLOCKED: "האתר חוסם סריקה אוטומטית. הפתרון הוא מקור גיבוי (דף החברה בדרושים או בג'ובנט) ב-config/sources.yaml.",
    FailureKind.LAYOUT: "מבנה האתר השתנה והסורק לא מוצא את המשרות. צריך לעדכן את קוד הסריקה של האתר.",
    FailureKind.GONE: "הכתובת שהסורק פונה אליה כבר לא קיימת. צריך לעדכן את הכתובת או את מקור הנתונים.",
    FailureKind.CONFIG: "הגדרת המקור ב-config/sources.yaml שגויה.",
}

#: For a site that still works through its fallback board: the jobs are there, so the advice
#: is about the own-site scraper only.
DEGRADED_ADVICE = {
    FailureKind.TEMPORARY: "המשרות נאספות ממקור הגיבוי, כך שאין חוסר בנתונים. אתר החברה לא הגיב בזמן; אין צורך בפעולה כל עוד זה זמני.",
    FailureKind.BLOCKED: "המשרות נאספות ממקור הגיבוי, כך שאין חוסר בנתונים. אתר החברה חוסם סריקה אוטומטית; אין צורך בפעולה.",
    FailureKind.LAYOUT: "המשרות נאספות ממקור הגיבוי, כך שאין חוסר בנתונים. מבנה אתר החברה השתנה; כדאי לעדכן את קוד הסריקה שלו, כי באתר עצמו יש לרוב פרטים מלאים יותר.",
    FailureKind.GONE: "המשרות נאספות ממקור הגיבוי, כך שאין חוסר בנתונים. הכתובת באתר החברה כבר לא קיימת; כדאי לעדכן אותה.",
    FailureKind.CONFIG: "המשרות נאספות ממקור הגיבוי. הגדרת האתר ב-config/sources.yaml שגויה.",
}

KIND_LABELS = {
    FailureKind.TEMPORARY: "תקלה זמנית",
    FailureKind.BLOCKED: "חסימה",
    FailureKind.LAYOUT: "שינוי מבנה באתר",
    FailureKind.GONE: "כתובת לא קיימת",
    FailureKind.CONFIG: "שגיאת הגדרה",
}
