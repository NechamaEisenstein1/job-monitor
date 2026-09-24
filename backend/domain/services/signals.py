"""Honesty labels for a job, built from its postings' history:

* new    - first listed (by any agency) in the last hours.
* ghost  - open for a long time, or removed and re-published again and again: most
           likely a standing ad that is not a real opening.
* agencies - the same job advertised by several agencies. Applying through more than
           one gets candidates rejected, so the UI says "apply through one" and names
           the agency that listed it first.

Ages are only as old as our own records: a job listed before tracking began shows
the tracking start, so "open N days" means "at least N days"."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.config.settings import SignalsConfig
from backend.domain.models import PostingHistory
from backend.domain.services.normalization import comparison_key


def posting_key(source_job_id: str | None, url_fingerprint: str) -> str:
    """Same identity rule as the pipeline: the site's id when it has one, else the URL."""
    return f"id:{source_job_id}" if source_job_id else f"url:{url_fingerprint}"


def title_key(title: str | None) -> str:
    return comparison_key(title)[:300]


@dataclass(frozen=True)
class JobSignals:
    open_since: datetime | None
    days_open: int | None
    reposts: int
    is_new: bool
    is_ghost: bool
    agency_count: int
    first_agency: str | None


class SignalPolicy:
    def __init__(self, cfg: SignalsConfig):
        self._cfg = cfg

    def compute(self, histories: Iterable[PostingHistory], now: datetime) -> JobSignals:
        rows = list(histories)
        if not rows:
            return JobSignals(None, None, 0, False, False, 0, None)
        first = min(rows, key=lambda h: h.origin_first_seen_at)
        open_since = first.origin_first_seen_at
        days_open = max(0, (now - open_since).days)
        reposts = max(h.reposts for h in rows)
        return JobSignals(
            open_since=open_since,
            days_open=days_open,
            reposts=reposts,
            is_new=now - open_since <= timedelta(hours=self._cfg.new_within_hours) and reposts == 0,
            is_ghost=days_open >= self._cfg.ghost_after_days or reposts >= self._cfg.ghost_min_reposts,
            agency_count=len({h.recruitment_company for h in rows}),
            first_agency=first.recruitment_company,
        )
