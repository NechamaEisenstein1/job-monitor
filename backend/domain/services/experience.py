"""Reads the years of experience a posting requires (Hebrew and English).

Only lines that talk about experience are considered, and lines marked as an advantage
("יתרון", "advantage", "preferred") are ignored - they are nice-to-haves, not requirements.
The result is the HIGHEST mandatory requirement: a job that needs 5 years in X is not a
junior job even if another line asks for one year in Y.

"N+" ("2+", "+2", "2 ומעלה", "מעל 2", "more than 2") and a range starting at N ("2-3") mean
MORE than N and are returned as N + OPEN_ENDED, so "2 years" is level A while "2+" is level B.
"At least N" ("לפחות שנתיים") is a plain N-year requirement."""
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
# Added to N for "more than N" (N+, N-M ranges); small enough never to look like a real value.
OPEN_ENDED = 0.01
# "3", "3+", "+3", "3-4", "3 – 5", "1.5" followed by a year unit; an optional "עד"/"up to" before it.
_MORE_WORDS = r"ומעלה|או\s+יותר|and\s+above|or\s+more"
# A leading "+" counts only on its own ("+2", "ניסיון +2"), never the end of "C++".
_DIGITS = re.compile(rf"(עד\s*|up\s+to\s*)?((?<![\w+])\+\s*)?(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?))?"
                     rf"\s*(\+|{_MORE_WORDS})?\s*{_UNIT}", re.IGNORECASE)
# After the unit: "2 שנים+", "2 years or more", also past the word experience: "2 שנות ניסיון ומעלה".
# (A "+" after "ניסיון" usually means "and", e.g. "ניסיון + תואר", so only words count there.)
_MORE_AFTER = re.compile(rf"^\s*(?:\+|{_MORE_WORDS}|\bplus\b|(?:of\s+)?(?:ניסיון|נסיון|experience)\s+(?:{_MORE_WORDS}))",
                         re.IGNORECASE)
_MORE_BEFORE = re.compile(r"(?:מעל|יותר\s+מ-?|more\s+than|over|above)\s*$", re.IGNORECASE)
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
        values = []
        for m in _DIGITS.finditer(line):
            up_to, plus_before, low, high, plus_after = m.groups()
            if up_to:
                values.append(0.0)
                continue
            more = (plus_before or plus_after or (high and float(high) > float(low))
                    or _MORE_AFTER.search(line[m.end():]) or _MORE_BEFORE.search(line[:m.start()]))
            values.append(float(low) + (OPEN_ENDED if more else 0))
        numbered = _DIGITS.sub(" ", line)  # don't count "3 שנים" twice
        for m in _WORDS.finditer(numbered):
            up_to, word = m.group(1), m.group(2).lower()
            # Hebrew number words need a unit or the word "שנתיים" itself to mean years.
            if word in ("שנתיים", "שנה אחת") or re.search(rf"{re.escape(word)}\s+(?:שנות|שנים|years?)", numbered, re.I):
                if up_to:
                    values.append(0.0)
                    continue
                more = _MORE_AFTER.search(numbered[m.end():]) or _MORE_BEFORE.search(numbered[:m.start()]) \
                    or re.search(r"(?<![\w+])\+\s*$", numbered[:m.start()])
                values.append(float(_WORD_NUMBERS[word]) + (OPEN_ENDED if more else 0))
        if not values:
            for match in _ONE_YEAR.finditer(numbered):
                values.append(0.0 if match.group(1) else 1.0)
        found.extend(values)
    if not found:
        return None
    return max(found)


def format_years(years: float) -> str:
    """2 -> "2", 2.01 (open-ended) -> "2+", 1.5 -> "1.5"."""
    base = round(years - OPEN_ENDED, 1)
    return f"{base:g}+" if abs(years - base - OPEN_ENDED) < 1e-9 else f"{years:g}"
