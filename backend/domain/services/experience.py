"""Reads the years of experience a posting requires (Hebrew and English).

Only lines that talk about experience are considered, and lines marked as an advantage
("יתרון", "advantage", "preferred") are ignored - they are nice-to-haves, not requirements.
The result is the HIGHEST mandatory requirement: a job that needs 5 years in X is not a
junior job even if another line asks for one year in Y."""
from __future__ import annotations

import re

_EXPERIENCE_LINE = re.compile(r"ניסיון|נסיון|experience|exp\b", re.IGNORECASE)
_OPTIONAL = re.compile(r"יתרון|advantage|preferred|nice to have|a plus|bonus", re.IGNORECASE)
_NO_EXPERIENCE = re.compile(r"ללא\s+(?:צורך\s+ב)?נ[י]?סיון|אין\s+צורך\s+בנ[י]?סיון|no\s+(?:prior\s+)?experience|"
                            r"entry[\s-]level|(?<!\d)0\s*[-–]\s*1\s*(?:years?|שנ)", re.IGNORECASE)

_WORD_NUMBERS = {
    "שנה אחת": 1, "שנת": 1, "שנה": 1, "שנתיים": 2,
    "שלוש": 3, "שלושה": 3, "ארבע": 4, "ארבעה": 4, "חמש": 5, "חמישה": 5,
    "שש": 6, "שישה": 6, "שבע": 7, "שבעה": 7, "שמונה": 8, "עשר": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "ten": 10,
}
_UNIT = r"(?:שנות|שנים|שנה|years?|yrs?)"
# "3", "3+", "3-4", "3 – 5", "1.5" followed by a year unit; an optional "עד"/"up to" before it.
_DIGITS = re.compile(rf"(עד\s*|up\s+to\s*)?(\d+(?:\.\d+)?)\s*(?:[-–]\s*\d+(?:\.\d+)?)?\s*\+?\s*{_UNIT}", re.IGNORECASE)
_WORDS = re.compile(
    r"(עד\s*|up\s+to\s*)?(?<![א-ת])(שנה אחת|שנתיים|שלושה|שלוש|ארבעה|ארבע|חמישה|חמש|שישה|שש|שבעה|שבע|שמונה|עשר"
    r"|one|two|three|four|five|six|seven|eight|ten)(?:\s+(?:שנות|שנים|years?))?(?![א-ת])", re.IGNORECASE)
# A bare "שנה" / "שנת ניסיון" (one year): "ניסיון של שנה", "לפחות שנה", "שנת ניסיון".
_ONE_YEAR = re.compile(r"(עד\s*)?(?:(?<=של\s)|(?<=לפחות\s)|(?<=מינימום\s)|(?<=\s)|^)(?:שנה|שנת)(?=\s+(?:ניסיון|נסיון|לפחות|ומעלה)|\s*$|[\s,.;:)-])")


def required_years(text: str) -> float | None:
    """Highest mandatory years of experience, 0 for "no experience needed", None if unstated."""
    found: list[float] = []
    for line in re.split(r"[\n•●▪;]|(?<=[.!?])\s", text or ""):
        if _OPTIONAL.search(line):
            continue
        if _NO_EXPERIENCE.search(line):  # "entry level", "0-1 years" need no word "experience"
            found.append(0)
            continue
        if not _EXPERIENCE_LINE.search(line):
            continue
        values = [0.0 if up_to else float(n) for up_to, n in _DIGITS.findall(line)]
        numbered = _DIGITS.sub(" ", line)  # don't count "3 שנים" twice
        for up_to, word in _WORDS.findall(numbered):
            word = word.lower()
            # Hebrew number words need a unit or the word "שנתיים" itself to mean years.
            if word in ("שנתיים", "שנה אחת") or re.search(rf"{re.escape(word)}\s+(?:שנות|שנים|years?)", numbered, re.I):
                values.append(0.0 if up_to else float(_WORD_NUMBERS[word]))
        if not values:
            for match in _ONE_YEAR.finditer(numbered):
                values.append(0.0 if match.group(1) else 1.0)
        found.extend(values)
    if not found:
        return None
    return max(found)
