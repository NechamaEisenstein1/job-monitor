"""Shared HTML/text helpers for site scrapers. Extraction only - no scoring, no matching."""
from __future__ import annotations

import re
from collections.abc import Iterable

from bs4 import BeautifulSoup, Tag

# Headings Israeli job posts use to start the requirements section.
REQUIREMENT_MARKERS: tuple[str, ...] = (
    "דרישות המשרה", "דרישות התפקיד", "דרישות", "למי התפקיד יתאים", "מה אנחנו מחפשים",
    "Requirements", "Qualifications",
)
_BULLET = re.compile(r"^[\s•●▪·\-–*]+")


def soup(markup: str) -> BeautifulSoup:
    return BeautifulSoup(markup, "html.parser")


def text_of(node: Tag | None) -> str:
    """Readable multi-line text of an element; empty string for None."""
    if node is None:
        return ""
    for br in node.find_all("br"):
        br.replace_with("\n")
    lines = (line.strip() for line in node.get_text("\n").splitlines())
    return "\n".join(line for line in lines if line)


def html_to_text(fragment: str | None) -> str:
    return text_of(soup(fragment)) if fragment else ""


def first_text(node: Tag, selector: str) -> str:
    found = node.select_one(selector)
    return found.get_text(" ", strip=True) if found else ""


def split_requirements(text: str, markers: Iterable[str] = REQUIREMENT_MARKERS) -> tuple[str, str]:
    """Split a posting at the first line that starts a requirements section.

    Returns (description, requirements). Without a marker, everything is description."""
    lines = text.splitlines()
    for i, raw in enumerate(lines):
        line = _BULLET.sub("", raw).strip()
        for marker in markers:
            if line.startswith(marker):
                rest = line[len(marker):].lstrip(" :：-–?？")
                requirements = "\n".join(([rest] if rest else []) + lines[i + 1:]).strip()
                return "\n".join(lines[:i]).strip(), requirements
    return text.strip(), ""


def drop_lines(text: str, unwanted: Iterable[str]) -> str:
    unwanted = {u.strip() for u in unwanted if u and u.strip()}
    return "\n".join(line for line in text.splitlines() if line.strip() not in unwanted)


def block_around(document: BeautifulSoup, anchor: str, min_chars: int = 150) -> Tag | None:
    """The smallest element containing `anchor` text with at least `min_chars` of text.
    Used for page-builder sites (Elementor) whose markup has no stable job classes."""
    node = document.find(string=re.compile(re.escape(anchor)))
    if node is None:
        return None
    element = node.parent
    while element is not None and len(element.get_text(strip=True)) < min_chars:
        element = element.parent
    return element
