from datetime import timedelta

import pytest

from backend.config.settings import RunStatusConfig
from backend.domain.enums import JobSourceStatus as S, JobStatus, RunStatus, ScrapeStatus
from backend.domain.models import ScraperRun
from backend.domain.services.archive import ArchiveService
from backend.domain.services.run_status import compute_run_status

from tests.conftest import NOW


@pytest.fixture
def archive(cfg):
    return ArchiveService(cfg.archive)  # warn 30d, archive 60d, min 3 successful runs


def test_recently_seen_stays_active(archive):
    assert archive.source_status(S.ACTIVE, NOW - timedelta(days=5), NOW, 10) == S.ACTIVE


def test_not_seen_recently(archive):
    assert archive.source_status(S.ACTIVE, NOW - timedelta(days=31), NOW, 10) == S.NOT_SEEN_RECENTLY


def test_archive(archive):
    assert archive.source_status(S.NOT_SEEN_RECENTLY, NOW - timedelta(days=61), NOW, 10) == S.ARCHIVED


def test_failed_scraper_does_not_archive(archive):
    # 90 days missing, but the site hasn't scraped successfully enough since.
    assert archive.source_status(S.ACTIVE, NOW - timedelta(days=90), NOW, 2) == S.ACTIVE


def test_job_status_derived_from_sources():
    assert ArchiveService.job_status([S.ARCHIVED, S.ACTIVE]) == JobStatus.ACTIVE
    assert ArchiveService.job_status([S.ARCHIVED, S.NOT_SEEN_RECENTLY]) == JobStatus.NOT_SEEN_RECENTLY
    assert ArchiveService.job_status([S.ARCHIVED]) == JobStatus.ARCHIVED


RUN_CFG = RunStatusConfig(success_ratio=0.9, partial_ratio=0.5)


def runs(ok: int, failed: int) -> list[ScraperRun]:
    def one(status):
        return ScraperRun(None, "r", "site", status, NOW, NOW, 0, 0, 0, None, None)
    return [one(ScrapeStatus.SUCCESS)] * ok + [one(ScrapeStatus.TIMEOUT)] * failed


@pytest.mark.parametrize("ok, failed, expected", [
    (10, 0, RunStatus.SUCCESS),   # 100%
    (9, 1, RunStatus.SUCCESS),    # 90%
    (1, 1, RunStatus.PARTIAL),    # 50%
    (4, 6, RunStatus.FAILED),     # below 50%
    (0, 0, RunStatus.FAILED),     # zero scrapers
])
def test_run_status(ok, failed, expected):
    assert compute_run_status(runs(ok, failed), RUN_CFG) == expected


def test_zero_results_is_not_success():
    zero = [ScraperRun(None, "r", "s", ScrapeStatus.ZERO_RESULTS, NOW, NOW, 0, 0, 0, None, None)]
    assert compute_run_status(zero, RUN_CFG) == RunStatus.FAILED
