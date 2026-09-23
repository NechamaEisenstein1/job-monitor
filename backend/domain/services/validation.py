from backend.domain.models import NormalizedJob


def validate_job(job: NormalizedJob) -> list[str]:
    """Returns the reasons a record is invalid; empty list means valid."""
    errors = []
    if not job.title:
        errors.append("missing_title")
    if not job.source_url:
        errors.append("missing_source_url")
    elif not job.source_url.startswith(("https://", "http://")):
        errors.append("invalid_source_url")
    if not job.recruitment_company:
        errors.append("missing_recruitment_company")
    return errors
