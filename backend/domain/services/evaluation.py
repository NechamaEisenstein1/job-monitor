"""Junior / entry-level eligibility. The only business scoring in the system."""
from __future__ import annotations

from datetime import datetime

from backend.config.settings import JuniorKeywords, JuniorScoring, LocationsConfig, MatchingConfig
from backend.domain.models import Job, JobEvaluation
from backend.domain.services.classification import (
    GovernmentTenderDetector, RankingPolicy, RoleClassifier, keyword_pattern,
)
from backend.domain.services.experience import required_years
from backend.domain.services.normalization import comparison_key


class LocationMatcher:
    def __init__(self, cfg: LocationsConfig):
        self._tiers = {
            "primary": [(loc, comparison_key(loc)) for loc in cfg.primary],
            "secondary": [(loc, comparison_key(loc)) for loc in cfg.secondary],
        }
        self._search_text = cfg.search_text_when_missing

    def match_rule(self, job: Job) -> str | None:
        if job.location or job.region:
            return self._match(f"{comparison_key(job.location)} {comparison_key(job.region)}", "location")
        if self._search_text:
            text = " ".join(comparison_key(t) for t in (job.title, job.description, job.requirements))
            return self._match(text, "location_in_text")
        return None

    def _match(self, text: str, rule: str) -> str | None:
        text = f" {text} "
        for tier, locations in self._tiers.items():
            for label, key in locations:
                if key and key in text:
                    return f"{rule}:{tier}:{label}"
        return None

    def matches(self, job: Job) -> bool:
        return self.match_rule(job) is not None


class JobEvaluationService:
    """is_eligible = location matches AND junior_score >= threshold AND role type is eligible.
    The individual facets are stored too, so per-user matching can reuse them."""

    def __init__(
        self,
        keywords: JuniorKeywords,
        scoring: JuniorScoring,
        threshold: float,
        location_matcher: LocationMatcher,
        role_classifier: RoleClassifier,
        tender_detector: GovernmentTenderDetector,
        ranking: RankingPolicy,
        junior_max_years: float = 2,
    ):
        self._groups = [
            ("strong_positive", scoring.strong_positive, keywords.strong_positive),
            ("medium_positive", scoring.medium_positive, keywords.medium_positive),
            ("strong_negative", scoring.strong_negative, keywords.strong_negative),
        ]
        self._patterns = {kw: keyword_pattern(kw) for _, _, kws in self._groups for kw in kws}
        self._base = scoring.base
        self._threshold = threshold
        self._location = location_matcher
        self._roles = role_classifier
        self._tenders = tender_detector
        self._ranking = ranking
        self._max_years = junior_max_years

    @classmethod
    def from_config(cls, cfg: MatchingConfig, threshold: float | None = None) -> "JobEvaluationService":
        return cls(
            cfg.junior_keywords, cfg.junior_scoring,
            cfg.thresholds.junior_score if threshold is None else threshold,
            LocationMatcher(cfg.locations), RoleClassifier(cfg.roles),
            GovernmentTenderDetector(cfg.government), RankingPolicy(cfg.ranking),
            cfg.experience.junior_max_years,
        )

    def junior_score(self, job: Job) -> tuple[float, list[str]]:
        text = "\n".join([job.title, job.description, job.requirements]).casefold()
        score = self._base
        rules = []
        for group, weight, keywords in self._groups:
            for kw in keywords:
                if self._patterns[kw].search(text):
                    score += weight
                    rules.append(f"{group}:{kw}")
        return round(min(1.0, max(0.0, score)), 4), rules

    def _seniority(self, job: Job, score: float, matched: list[str]) -> tuple[bool, float, str | None, str | None]:
        """-> (is_junior, adjusted score, matched rule, rejection).

        Stated experience decides first: above the ceiling is never junior; at or below
        it is junior unless a senior/lead keyword says otherwise. Without a stated
        requirement the keyword score decides. The score is kept consistent with the
        verdict so the UI never shows a junior job with a failing score."""
        years = required_years("\n".join([job.title, job.description, job.requirements]))
        senior_keyword = any(r.startswith("strong_negative:") for r in matched)
        if years is not None and years > self._max_years:
            return False, min(score, round(self._threshold - 0.1, 4)), None, \
                f"experience_required ({years:g} > {self._max_years:g} years)"
        if years is not None and not senior_keyword:
            return True, max(score, self._threshold), f"experience:{years:g}y", None
        if score >= self._threshold:
            return True, score, None, None
        return False, score, None, f"junior_score_below_threshold ({score} < {self._threshold})"

    def evaluate(self, job: Job, scrape_run_id: str | None, now: datetime) -> JobEvaluation:
        if job.id is None:
            raise ValueError("Only persisted jobs can be evaluated")
        score, matched = self.junior_score(job)
        rejections = []

        location_rule = self._location.match_rule(job)
        if location_rule:
            matched.append(location_rule)
        else:
            rejections.append("location_not_matched")

        is_junior, score, rule, rejection = self._seniority(job, score, matched)
        if rule:
            matched.append(rule)
        if rejection:
            rejections.append(rejection)

        role_type = self._roles.classify(job)
        matched.append(f"role:{role_type}")
        if not self._roles.is_eligible_type(role_type):
            rejections.append(f"role_not_eligible ({role_type})")

        is_tender = self._tenders.is_tender(job)
        if is_tender:
            matched.append("government_tender")

        return JobEvaluation(
            job_id=job.id,
            scrape_run_id=scrape_run_id,
            junior_score=score,
            is_eligible=not rejections,
            matched_rules=matched,
            rejection_reasons=rejections,
            created_at=now,
            is_junior=is_junior,
            location_matched=location_rule is not None,
            role_type=role_type,
            is_government_tender=is_tender,
            rank_score=self._ranking.rank(is_junior=is_junior, role_type=role_type, junior_score=score),
        )
