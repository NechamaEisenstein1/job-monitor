from backend.domain.models import RawJob
from backend.domain.services.normalization import clip, normalize_raw_job


def test_clip_keeps_short_values_and_cuts_long_ones_at_a_word():
    assert clip("תל אביב", 200) == "תל אביב"
    assert clip(None, 200) is None
    clipped = clip("מרכז - תל אביב, פתח תקווה, רמת גן", 20)
    assert len(clipped) <= 20 and clipped.endswith("…") and clipped.startswith("מרכז - תל אביב")


def test_long_region_list_fits_the_location_column():
    # Drushim/JobNet sometimes list every region a job may be in (seen live: 260+ chars).
    regions = "; ".join(["מרכז - תל אביב, פתח תקווה, רמת גן וגבעתיים, בקעת אונו"] * 6)
    job = normalize_raw_job(RawJob(
        recruitment_company="X", source_job_id=None, source_url="https://example.com/1", title="t",
        description="", requirements="", client_company=None, employment_type=None,
        location=regions, region=None, published_at=None))
    assert len(job.location) <= 200
