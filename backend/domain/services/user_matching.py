"""Which jobs suit which user. Pure: works on evaluation facets, never re-scores."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from backend.domain.enums import ExperienceLevel
from backend.domain.models import Job, JobEvaluation, Recruiter
from backend.domain.services.normalization import company_key


def matches_profile(evaluation: JobEvaluation, level: ExperienceLevel, eligible_role_types: Iterable[str]) -> bool:
    """Location and role type always apply. Junior users get junior roles only;
    experienced users get every seniority."""
    if not evaluation.location_matched or evaluation.role_type not in set(eligible_role_types):
        return False
    return evaluation.is_junior if level == ExperienceLevel.JUNIOR else True


def recruiters_at(job: Job, recruitment_companies: Iterable[str], recruiters: Iterable[Recruiter]) -> list[Recruiter]:
    """The user's saved contacts who work at the hiring client or at an agency listing the job."""
    companies = {company_key(c) for c in [job.client_company, *recruitment_companies] if c}
    companies.discard("")
    return [r for r in recruiters if company_key(r.company) in companies]


@dataclass(frozen=True)
class AlertItem:
    job_id: int
    title: str
    location: str | None
    client_company: str | None
    junior_score: float
    is_government_tender: bool
    source_urls: list[str]
    recruiter_names: list[str]

    @property
    def priority(self) -> tuple[int, int, float]:
        """Government tenders first, then jobs where the user knows a recruiter."""
        return (int(self.is_government_tender), int(bool(self.recruiter_names)), self.junior_score)
