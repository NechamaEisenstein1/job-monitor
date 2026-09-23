from backend.domain.models import RawJob
from backend.domain.services.normalization import normalize_url, url_fingerprint
from backend.domain.services.source_identity import SourceIdentityResolver


def raw(source_job_id=None, url="https://example.com/jobs/1"):
    return RawJob(recruitment_company=" Matrix ", source_job_id=source_job_id, source_url=url, title="t",
                  description="", requirements="", client_company=None, employment_type=None,
                  location=None, region=None, published_at=None)


def test_source_job_id_exists_is_identity():
    a = SourceIdentityResolver().resolve(raw("M-1", "https://example.com/a"))
    b = SourceIdentityResolver().resolve(raw("M-1", "https://example.com/b"))
    assert a.uses_source_job_id
    assert (a.recruitment_company, a.source_job_id) == (b.recruitment_company, b.source_job_id) == ("Matrix", "M-1")


def test_source_job_id_missing_falls_back_to_url_fingerprint():
    identity = SourceIdentityResolver().resolve(raw(None, "https://example.com/jobs/1"))
    assert not identity.uses_source_job_id
    assert identity.source_url_fingerprint == url_fingerprint("https://example.com/jobs/1")


def test_blank_source_job_id_counts_as_missing():
    assert not SourceIdentityResolver().resolve(raw("  ")).uses_source_job_id


def test_url_fingerprint_is_deterministic_and_ignores_noise():
    variants = [
        "https://example.com/jobs/1",
        "http://www.EXAMPLE.com/jobs/1/",
        "https://example.com/jobs/1?utm_source=mail&utm_campaign=x",
        "https://example.com:443/jobs/1#apply",
    ]
    assert len({url_fingerprint(v) for v in variants}) == 1
    assert len(url_fingerprint(variants[0])) == 64


def test_url_fingerprint_keeps_meaningful_query_and_path():
    assert url_fingerprint("https://example.com/job?id=1") != url_fingerprint("https://example.com/job?id=2")
    assert url_fingerprint("https://example.com/jobs/1") != url_fingerprint("https://example.com/jobs/2")
    assert normalize_url("https://x.com/j?b=2&a=1") == normalize_url("https://x.com/j?a=1&b=2")
