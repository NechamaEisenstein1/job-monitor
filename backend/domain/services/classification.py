"""Role type and government-tender classification. Config-driven, pure."""
from __future__ import annotations

import re

from backend.config.settings import GovernmentConfig, RankingConfig, RolesConfig
from backend.domain.models import Job

OTHER = "other"


def keyword_pattern(keyword: str) -> re.Pattern[str]:
    # Block adjacent Latin letters/digits ("rf" must not hit "rfc") but allow Hebrew
    # prefixes and suffixes ("למפתחת" still contains "מפתח").
    return re.compile(rf"(?<![a-z0-9]){re.escape(keyword.casefold())}(?![a-z0-9])")


class RoleClassifier:
    def __init__(self, cfg: RolesConfig):
        # Order matters: the first type whose keyword hits wins.
        self._types = [(name, [keyword_pattern(k) for k in words]) for name, words in cfg.types.items()]
        self._eligible = set(cfg.eligible_types)

    def classify(self, job: Job) -> str:
        # Title only: descriptions mention "בדיקות" / "פיתוח" in passing far too often
        # (a live sample put 431 analysts and cyber roles under "qa" via descriptions).
        return self._first_type(job.title.casefold()) or OTHER

    def is_eligible_type(self, role_type: str) -> bool:
        return role_type in self._eligible

    def _first_type(self, text: str) -> str | None:
        for name, patterns in self._types:
            if any(p.search(text) for p in patterns):
                return name
        return None


class GovernmentTenderDetector:
    def __init__(self, cfg: GovernmentConfig):
        self._patterns = [keyword_pattern(k) for k in cfg.keywords]

    def is_tender(self, job: Job) -> bool:
        text = "\n".join([job.title, job.description, job.requirements, job.client_company or ""]).casefold()
        return any(p.search(text) for p in self._patterns)


class RankingPolicy:
    def __init__(self, cfg: RankingConfig):
        self._cfg = cfg

    def rank(self, *, is_junior: bool, role_type: str, junior_score: float) -> float:
        priority = self._cfg.role_priority
        position = priority.index(role_type) if role_type in priority else len(priority)
        role_points = (len(priority) - position) * self._cfg.role_step
        return round((self._cfg.junior_bonus if is_junior else 0) + role_points + junior_score * 10, 4)
