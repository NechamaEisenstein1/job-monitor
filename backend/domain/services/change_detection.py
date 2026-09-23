from backend.domain.enums import JobChange
from backend.domain.models import Job, JobSource


def detect_change(
    current: Job,
    previous: Job | None,
    current_source: JobSource,
    previous_source: JobSource | None = None,
) -> JobChange | None:
    """`previous` / `previous_source` are the states before this observation
    (None = did not exist). Seeing an unchanged job again is not a change."""
    if previous is None:
        return JobChange.NEW
    if current.content_hash != previous.content_hash:
        return JobChange.CONTENT_UPDATED
    if previous_source is None:
        return JobChange.NEW_SOURCE
    # Compare fingerprints, not raw strings: tracking params, www, slashes don't count.
    if previous_source.source_url_fingerprint != current_source.source_url_fingerprint:
        return JobChange.SOURCE_URL_UPDATED
    return None
