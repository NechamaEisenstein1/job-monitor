"""Read models of the guide articles, for the public pages and the admin editor."""
from __future__ import annotations

from datetime import date

from backend.application.dto import Dto, UtcDatetime


class ArticleSourceDto(Dto):
    name: str
    url: str


class ArticleBlockDto(Dto):
    kind: str            # heading | paragraph | list
    text: str
    items: list[str]


class ArticleSummaryDto(Dto):
    id: int
    slug: str
    title: str
    summary: str
    published_on: date
    is_published: bool
    reading_minutes: int
    updated_at: UtcDatetime


class ArticleDto(ArticleSummaryDto):
    blocks: list[ArticleBlockDto]
    sources: list[ArticleSourceDto]


class EditableArticleDto(ArticleSummaryDto):
    """The article as the admin wrote it: the body in its text format, not split into blocks."""
    body: str
    sources: list[ArticleSourceDto]
