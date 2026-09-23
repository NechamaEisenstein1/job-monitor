from backend.domain.models import NormalizedJob, RawJob, SourceIdentity
from backend.domain.services.normalization import clean_text, url_fingerprint


class SourceIdentityResolver:
    """(recruitment_company, source_job_id) when the source gives an id,
    otherwise (recruitment_company, source_url_fingerprint). job_id is never involved."""

    def resolve(self, raw_job: RawJob | NormalizedJob) -> SourceIdentity:
        return SourceIdentity(
            recruitment_company=clean_text(raw_job.recruitment_company) or "",
            source_job_id=clean_text(raw_job.source_job_id),
            source_url_fingerprint=url_fingerprint(raw_job.source_url),
        )
