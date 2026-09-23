import pytest

from backend.config.settings import RetentionConfig, RunStatusConfig
from backend.domain.enums import JobSourceStatus as S, JobStatus, RunStatus, ScrapeStatus
from backend.domain.models import ScraperRun
from backend.domain.services.retention import RetentionPolicy, derive_job_status
from backend.domain.services.run_status import compute_run_status

from tests.conftest import NOW

policy = RetentionPolicy(RetentionConfig(max_prune_ratio=0.5))


def test_successful_site_prunes_unlisted_postings():
    assert policy.decide(site_succeeded=True, unseen=3, total=100).prune


def test_failed_site_never_prunes():
    decision = policy.decide(site_succeeded=False, unseen=100, total=100)
    assert not decision.prune and decision.reason == "site_failed"


def test_nothing_unseen_is_a_no_op():
    assert not policy.decide(site_succeeded=True, unseen=0, total=100).prune


def test_implausible_mass_removal_is_skipped():
    decision = policy.decide(site_succeeded=True, unseen=80, total=100)
    assert not decision.prune and "80 of 100" in decision.reason
    assert policy.decide(site_succeeded=True, unseen=50, total=100).prune  # exactly at the limit


def test_job_status_derived_from_sources():
    assert derive_job_status([S.ARCHIVED, S.ACTIVE]) == JobStatus.ACTIVE
    assert derive_job_status([S.ARCHIVED, S.NOT_SEEN_RECENTLY]) == JobStatus.NOT_SEEN_RECENTLY
    assert derive_job_status([S.ARCHIVED]) == JobStatus.ARCHIVED


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
