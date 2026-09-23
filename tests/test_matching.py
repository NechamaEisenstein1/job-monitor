from backend.domain.models import JobCandidate
from backend.domain.services.matching import JobMatcher

from tests.conftest import make_job

matcher = JobMatcher(title_threshold=0.8)


def cand(title="Junior Backend Developer", company="Intel", location="Jerusalem"):
    return JobCandidate(title=title, client_company=company, location=location)


def test_exact_normalized_match():
    job = make_job(title="junior  backend-developer!")
    assert matcher.find_match(cand(), [], [job]) is job


def test_fuzzy_title_match():
    job = make_job(title="Junior Backend Developer (Python)")
    assert matcher.find_match(cand(company="Intel Ltd"), [], [job]) is job


def test_different_company_does_not_match():
    assert matcher.find_match(cand(company="Wix"), [], [make_job()]) is None


def test_different_location_does_not_match():
    assert matcher.find_match(cand(location="Tel Aviv"), [], [make_job()]) is None


def test_below_threshold_does_not_match():
    assert matcher.find_match(cand(title="Senior Frontend Engineer"), [], [make_job()]) is None


def test_title_alone_is_not_enough_evidence():
    job = make_job(client_company=None, location=None)
    assert matcher.find_match(cand(company=None, location=None), [], [job]) is None


def test_job_already_holding_a_posting_from_the_same_agency_is_excluded():
    taken, free = make_job(id=1), make_job(id=2)
    assert matcher.find_match(cand(), [], [taken, free], excluded_job_ids={1}) is free
    assert matcher.find_match(cand(), [], [taken], excluded_job_ids={1}) is None


def test_current_run_jobs_take_precedence_and_result_is_deterministic():
    old = make_job(id=1)
    current = make_job(id=9)
    assert matcher.find_match(cand(), [current], [old]) is current
    a, b = make_job(id=5), make_job(id=3)
    assert matcher.find_match(cand(), [], [a, b]) is b  # same score -> lowest id
