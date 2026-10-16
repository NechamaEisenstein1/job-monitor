"""Junior / entry-level eligibility. The only business scoring in the system."""
from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime

from backend.config.settings import JuniorKeywords, JuniorScoring, LocationsConfig, MatchingConfig, RegionConfig
from backend.domain.models import Job, JobEvaluation
from backend.domain.services.classification import (
    GovernmentTenderDetector, RankingPolicy, RoleClassifier, keyword_pattern,
)
from backend.domain.services.experience import format_years, required_years
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


_HEBREW = re.compile(r"[\u0590-\u05ff]")


def place_pattern(phrase: str) -> re.Pattern[str] | None:
    """Whole-word match of a place or area phrase in comparison_key() text.

    "יהוד" must not hit "יהודה", nor "אילת" hit "שאילתות". A Hebrew phrase may carry
    the prefixes ו/ב/ל/מ ("בבאר שבע", "ומתל אביב"), but not ה/ש/כ, which turn
    places into ordinary words ("הגדרה" is not "גדרה")."""
    key = comparison_key(phrase)
    if not key:
        return None
    prefix = "ו?[בלמ]?" if _HEBREW.match(key) else ""
    return re.compile(rf"(?<!\S){prefix}{re.escape(key)}(?!\S)")


class RegionMatcher:
    """Which of the configured regions a job is in (see `regions` in matching.yaml)."""

    def __init__(self, regions: Iterable[RegionConfig], search_text_when_missing: bool = True):
        compile_all = lambda phrases: [p for p in map(place_pattern, phrases) if p]  # noqa: E731
        self._regions = [(r.code, compile_all(r.places), compile_all(r.area_words)) for r in regions]
        self._search_text = search_text_when_missing

    def regions(self, job: Job) -> list[str]:
        if job.location or job.region:
            text = f"{comparison_key(job.location)} {comparison_key(job.region)}"
            return [code for code, places, words in self._regions
                    if any(p.search(text) for p in (*places, *words))]
        if not self._search_text:
            return []
        text = " ".join(comparison_key(t) for t in (job.title, job.description, job.requirements))
        return [code for code, places, _ in self._regions if any(p.search(text) for p in places)]


def regions_field(codes: Iterable[str]) -> str:
    """["jerusalem", "center"] -> "|jerusalem|center|" (searchable with LIKE '%|code|%')."""
    codes = list(codes)
    return f"|{'|'.join(codes)}|" if codes else ""


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
        junior_title_keywords: tuple[str, ...] = (),
        region_matcher: RegionMatcher | None = None,
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
        self._title_patterns = [keyword_pattern(k) for k in junior_title_keywords]
        self._regions = region_matcher or RegionMatcher(())

    @classmethod
    def from_config(cls, cfg: MatchingConfig, threshold: float | None = None) -> "JobEvaluationService":
        return cls(
            cfg.junior_keywords, cfg.junior_scoring,
            cfg.thresholds.junior_score if threshold is None else threshold,
            LocationMatcher(cfg.locations), RoleClassifier(cfg.roles),
            GovernmentTenderDetector(cfg.government), RankingPolicy(cfg.ranking),
            cfg.experience.junior_max_years, cfg.experience.junior_title_keywords,
            RegionMatcher(cfg.regions, cfg.locations.search_text_when_missing),
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

    def _seniority(self, years: float | None, score: float,
                   matched: list[str]) -> tuple[bool, float, str | None, str | None]:
        """-> (is_junior, adjusted score, matched rule, rejection).

        Stated experience decides first: above the ceiling is never junior; at or below
        it is junior unless a senior/lead keyword says otherwise. Without a stated
        requirement the keyword score decides. The score is kept consistent with the
        verdict so the UI never shows a junior job with a failing score."""
        senior_keyword = any(r.startswith("strong_negative:") for r in matched)
        if years is not None and years > self._max_years:
            return False, min(score, round(self._threshold - 0.1, 4)), None, \
                f"experience_required ({format_years(years)} > {self._max_years:g} years)"
        if years is not None and not senior_keyword:
            return True, max(score, self._threshold), f"experience:{format_years(years)}y", None
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

        years = required_years("\n".join([job.title, job.description, job.requirements]))
        is_junior, score, rule, rejection = self._seniority(years, score, matched)
        if rule:
            matched.append(rule)
        if rejection:
            rejections.append(rejection)

        role_type = self._roles.classify(job)
        matched.append(f"role:{role_type}")
        if not self._roles.is_eligible_type(role_type):
            rejections.append(f"role_not_eligible ({role_type})")

        # A tender number or ministry (manual postings) is an explicit statement, stronger
        # than keyword detection, and must count before the rank is computed.
        is_tender = bool(job.tender_number or job.government_ministry) or self._tenders.is_tender(job)
        if is_tender:
            matched.append("government_tender")

        # "Junior" in the title, years above the junior ceiling in the requirements.
        title_mismatch = years is not None and years > self._max_years and \
            any(p.search(job.title.casefold()) for p in self._title_patterns)

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
            rank_score=self._ranking.rank(is_junior=is_junior, role_type=role_type, junior_score=score,
                                          is_government_tender=is_tender),
            required_years=years,
            junior_title_mismatch=title_mismatch,
            regions=regions_field(self._regions.regions(job)),
        )
