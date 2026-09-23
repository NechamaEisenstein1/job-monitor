from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from backend.config.settings import ArchiveConfig
from backend.domain.enums import JobSourceStatus, JobStatus


class ArchiveService:
    def __init__(self, cfg: ArchiveConfig):
        self._cfg = cfg

    def source_status(
        self,
        current: JobSourceStatus,
        last_seen_at: datetime,
        now: datetime,
        successful_site_runs_since_last_seen: int,
    ) -> JobSourceStatus:
        """Status for a source that was NOT seen in the current run.

        Absence only counts once its site has scraped successfully enough times
        since the source was last seen - a failing scraper proves nothing."""
        if successful_site_runs_since_last_seen < self._cfg.min_successful_site_runs_before_archive:
            return current
        days_missing = (now - last_seen_at).total_seconds() / 86400
        if days_missing >= self._cfg.archive_after_days:
            return JobSourceStatus.ARCHIVED
        if days_missing >= self._cfg.not_seen_warning_days:
            return JobSourceStatus.NOT_SEEN_RECENTLY
        return JobSourceStatus.ACTIVE

    @staticmethod
    def job_status(source_statuses: Iterable[JobSourceStatus]) -> JobStatus:
        statuses = set(source_statuses)
        if JobSourceStatus.ACTIVE in statuses:
            return JobStatus.ACTIVE
        if JobSourceStatus.NOT_SEEN_RECENTLY in statuses:
            return JobStatus.NOT_SEEN_RECENTLY
        return JobStatus.ARCHIVED
