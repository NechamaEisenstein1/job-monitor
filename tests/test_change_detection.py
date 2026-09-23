from dataclasses import replace

from backend.domain.enums import JobChange, JobSourceStatus
from backend.domain.models import JobSource
from backend.domain.services.change_detection import detect_change

from tests.conftest import NOW, make_job

SOURCE = JobSource(
    id=1, job_id=1, recruitment_company="Matrix", source_job_id="M-1", source_url="https://x.com/1",
    source_url_fingerprint="f" * 64, external_title="t", source_metadata_hash="h" * 64,
    first_seen_at=NOW, last_seen_at=NOW, status=JobSourceStatus.ACTIVE,
    first_scrape_run_id="r1", last_scrape_run_id="r1",
)


def test_new():
    assert detect_change(make_job(), None, SOURCE, None) == JobChange.NEW


def test_content_update():
    job = make_job()
    assert detect_change(replace(job, content_hash="b" * 64), job, SOURCE, SOURCE) == JobChange.CONTENT_UPDATED


def test_new_source():
    job = make_job()
    assert detect_change(job, replace(job), SOURCE, None) == JobChange.NEW_SOURCE


def test_url_update():
    job = make_job()
    moved = replace(SOURCE, source_url="https://x.com/moved", source_url_fingerprint="0" * 64)
    assert detect_change(job, replace(job), moved, SOURCE) == JobChange.SOURCE_URL_UPDATED


def test_cosmetic_url_difference_is_not_a_change():
    job = make_job()
    cosmetic = replace(SOURCE, source_url="https://www.x.com/1/?utm_source=mail")
    assert detect_change(job, replace(job), cosmetic, SOURCE) is None


def test_seen_again_unchanged_is_no_change():
    job = make_job()
    assert detect_change(job, replace(job), SOURCE, replace(SOURCE)) is None
