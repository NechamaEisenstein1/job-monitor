"""Daily refresh: the database holds only jobs the sites still publish.

A posting that a site no longer lists is removed - but only when that site scraped
successfully in this run (a failing scraper proves nothing), and only when the removal
looks plausible (a run that would wipe most of a site is far likelier a broken scraper
than a mass delisting)."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from backend.config.settings import RetentionConfig
from backend.domain.enums import JobSourceStatus, JobStatus


@dataclass(frozen=True)
class PruneDecision:
    prune: bool
    reason: str | None = None


class RetentionPolicy:
    def __init__(self, cfg: RetentionConfig):
        self._max_ratio = cfg.max_prune_ratio

    def decide(self, *, site_succeeded: bool, unseen: int, total: int) -> PruneDecision:
        """`total` = the site's postings before this run's removals; `unseen` = those not seen now."""
        if not site_succeeded:
            return PruneDecision(False, "site_failed")
        if unseen == 0:
            return PruneDecision(False)
        if total and unseen / total > self._max_ratio:
            return PruneDecision(False, f"would remove {unseen} of {total} postings "
                                        f"(> {self._max_ratio:.0%}); skipped as a likely scraper fault")
        return PruneDecision(True)


def derive_job_status(source_statuses: Iterable[JobSourceStatus]) -> JobStatus:
    """A job is active while any of its postings is."""
    statuses = set(source_statuses)
    if JobSourceStatus.ACTIVE in statuses:
        return JobStatus.ACTIVE
    if JobSourceStatus.NOT_SEEN_RECENTLY in statuses:
        return JobStatus.NOT_SEEN_RECENTLY
    return JobStatus.ARCHIVED
