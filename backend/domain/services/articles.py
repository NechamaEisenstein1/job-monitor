"""Article rules: validation and the light text format the admin writes the body in.
Pure functions - no persistence here.

Body format, one line at a time: "## " starts a heading, "- " a list item, any other line is a paragraph."""
from __future__ import annotations

import re
from datetime import date

from backend.domain.articles import ArticleBlock, ArticleDraft, ArticleInput, ArticleSource

TITLE_MIN, TITLE_MAX = 3, 200
SUMMARY_MAX = 400
BODY_MAX = 50_000
SLUG_MAX = 120
SOURCES_MAX = 20
HEBREW_WORDS_PER_MINUTE = 150

HEADING_PREFIX = "## "
LIST_ITEM_PREFIX = "- "
# Latin letters, digits and Hebrew letters, words joined by single hyphens.
SLUG_PATTERN = re.compile(r"[a-z0-9א-ת]+(?:-[a-z0-9א-ת]+)*")
URL_PATTERN = re.compile(r"https?://[^\s/$.?#][^\s]*", re.I)


class ArticleError(Exception):
    """User-facing failure. `code` is stable for the UI to translate; `status` is the HTTP status."""

    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


def parse_article_body(body: str) -> tuple[ArticleBlock, ...]:
    blocks: list[ArticleBlock] = []
    list_items: list[str] = []

    def close_list() -> None:
        if list_items:
            blocks.append(ArticleBlock("list", items=tuple(list_items)))
            list_items.clear()

    for line in (raw.strip() for raw in body.splitlines()):
        if line.startswith(LIST_ITEM_PREFIX):
            list_items.append(line.removeprefix(LIST_ITEM_PREFIX).strip())
            continue
        close_list()
        if line.startswith(HEADING_PREFIX):
            blocks.append(ArticleBlock("heading", text=line.removeprefix(HEADING_PREFIX).strip()))
        elif line:
            blocks.append(ArticleBlock("paragraph", text=line))
    close_list()
    return tuple(blocks)


def reading_minutes(body: str) -> int:
    return max(1, round(len(body.split()) / HEBREW_WORDS_PER_MINUTE))


def clean_article(raw: ArticleInput, today: date) -> ArticleDraft:
    return ArticleDraft(
        slug=_clean_slug(raw.slug), title=_clean_title(raw.title), summary=_clean_summary(raw.summary),
        body=_clean_body(raw.body), sources=_clean_sources(raw.sources), is_published=raw.is_published,
        published_on=raw.published_on or today,
    )


def _one_line(value: str) -> str:
    return " ".join(value.split())


def _clean_slug(value: str) -> str:
    slug = value.strip().lower()
    if not (slug and len(slug) <= SLUG_MAX and SLUG_PATTERN.fullmatch(slug)):
        raise ArticleError("article_bad_slug")
    return slug


def _clean_title(value: str) -> str:
    title = _one_line(value)
    if not TITLE_MIN <= len(title) <= TITLE_MAX:
        raise ArticleError("article_title_length")
    return title


def _clean_summary(value: str) -> str:
    summary = _one_line(value)
    if not 0 < len(summary) <= SUMMARY_MAX:
        raise ArticleError("article_summary_length")
    return summary


def _clean_body(value: str) -> str:
    body = "\n".join(line.rstrip() for line in value.strip().splitlines())
    if not parse_article_body(body):
        raise ArticleError("article_body_empty")
    if len(body) > BODY_MAX:
        raise ArticleError("article_body_too_long")
    return body


def _clean_sources(sources: list[tuple[str, str]]) -> tuple[ArticleSource, ...]:
    """Rows left completely empty in the form are skipped; a half-filled row is an error."""
    cleaned = tuple(ArticleSource(_one_line(name), url.strip()) for name, url in sources if name.strip() or url.strip())
    if len(cleaned) > SOURCES_MAX:
        raise ArticleError("article_too_many_sources")
    if not all(source.name and URL_PATTERN.fullmatch(source.url) for source in cleaned):
        raise ArticleError("article_bad_source")
    return cleaned
