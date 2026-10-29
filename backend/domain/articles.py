"""Guide articles the admin writes and publishes on the public site. All datetimes are naive UTC."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class ArticleSource:
    name: str
    url: str


@dataclass(frozen=True)
class ArticleBlock:
    """One piece of an article body, in reading order."""
    kind: str                       # heading | paragraph | list
    text: str = ""                  # heading and paragraph
    items: tuple[str, ...] = ()     # list


@dataclass(frozen=True)
class ArticleInput:
    """What the admin typed in the editor, before cleaning and validation."""
    slug: str
    title: str
    summary: str
    body: str
    sources: list[tuple[str, str]]  # (name, url)
    is_published: bool
    published_on: date | None       # None: today


@dataclass(frozen=True)
class ArticleDraft:
    """What the admin submits, already cleaned and validated."""
    slug: str
    title: str
    summary: str
    body: str
    sources: tuple[ArticleSource, ...]
    is_published: bool
    published_on: date


@dataclass(frozen=True)
class Article(ArticleDraft):
    id: int
    updated_at: datetime

    @property
    def path(self) -> str:
        return f"/articles/{self.slug}"
