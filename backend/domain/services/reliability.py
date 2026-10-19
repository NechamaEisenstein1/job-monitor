"""How reliable a listing is, from users' "the details are correct" votes."""
from __future__ import annotations

# Votes from different users needed for each level.
MEDIUM_AT = 1
HIGH_AT = 3

LEVELS = ("none", "medium", "high")


def reliability_level(verifications: int) -> str:
    if verifications >= HIGH_AT:
        return "high"
    if verifications >= MEDIUM_AT:
        return "medium"
    return "none"


def min_votes(level: str) -> int:
    """Votes needed to be at least this level (the board's reliability filter)."""
    return {"none": 0, "medium": MEDIUM_AT, "high": HIGH_AT}[level]
