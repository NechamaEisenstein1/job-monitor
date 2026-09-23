"""Cross-source matching: a heuristic, never identity, never a DB constraint."""
from __future__ import annotations

from collections.abc import Iterable, Set as AbstractSet
from difflib import SequenceMatcher

from backend.domain.models import Job, JobCandidate
from backend.domain.services.normalization import company_key, comparison_key


def _compatible(a: str, b: str) -> bool | None:
    """True = both known and equal, False = both known and different, None = unknown."""
    if not a or not b:
        return None
    return a == b


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, comparison_key(a), comparison_key(b)).ratio()


class JobMatcher:
    def __init__(self, title_threshold: float):
        self._threshold = title_threshold

    def score(self, candidate: JobCandidate, job: Job) -> float | None:
        """Title similarity if the job is a plausible match, else None."""
        company = _compatible(company_key(candidate.client_company), company_key(job.client_company))
        location = _compatible(comparison_key(candidate.location), comparison_key(job.location))
        if company is False or location is False:
            return None
        if not (company or location):
            return None  # a title alone is not enough evidence
        similarity = title_similarity(candidate.title, job.title)
        return similarity if similarity >= self._threshold else None

    def find_match(
        self,
        candidate: JobCandidate,
        current_run_jobs: Iterable[Job],
        existing_jobs: Iterable[Job],
        excluded_job_ids: AbstractSet[int] = frozenset(),
    ) -> Job | None:
        """`excluded_job_ids`: jobs that already carry a posting from the candidate's own
        recruitment company. An agency does not list one opening twice under different ids,
        so a second posting from the same agency is a different job, however similar."""
        # Jobs seen in this run take precedence over historical ones.
        for pool in (current_run_jobs, existing_jobs):
            best = self._best(candidate, (j for j in pool if j.id not in excluded_job_ids))
            if best is not None:
                return best
        return None

    def _best(self, candidate: JobCandidate, pool: Iterable[Job]) -> Job | None:
        scored = [(s, job) for job in pool if (s := self.score(candidate, job)) is not None]
        if not scored:
            return None
        # Deterministic: highest similarity, then oldest job.
        scored.sort(key=lambda pair: (-pair[0], pair[1].id or 0))
        return scored[0][1]
