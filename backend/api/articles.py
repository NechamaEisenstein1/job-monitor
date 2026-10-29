"""Guide articles: the JSON files in content/articles, shared with the frontend.

Each file name is the article's slug, so /articles/<slug> serves content/articles/<slug>.json."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

from backend.config.settings import PROJECT_ROOT

ARTICLES_DIR = PROJECT_ROOT / "content" / "articles"


@dataclass(frozen=True)
class ArticleSection:
    heading: str
    paragraphs: tuple[str, ...]
    points: tuple[str, ...]


@dataclass(frozen=True)
class ArticleSource:
    name: str
    url: str


@dataclass(frozen=True)
class Article:
    slug: str
    title: str
    summary: str
    published: date
    sections: tuple[ArticleSection, ...]
    sources: tuple[ArticleSource, ...]

    @property
    def path(self) -> str:
        return f"/articles/{self.slug}"


def load_articles(directory: Path = ARTICLES_DIR) -> tuple[Article, ...]:
    """Newest first (then by slug), the same order the articles page shows."""
    articles = [_parse_article(file.stem, json.loads(file.read_text(encoding="utf-8")))
                for file in directory.glob("*.json")]
    return tuple(sorted(articles, key=lambda a: (-a.published.toordinal(), a.slug)))


def _parse_article(slug: str, data: dict) -> Article:
    return Article(
        slug=slug,
        title=data["title"],
        summary=data["summary"],
        published=date.fromisoformat(data["published"]),
        sections=tuple(ArticleSection(s["heading"], tuple(s.get("paragraphs", ())), tuple(s.get("points", ())))
                       for s in data["sections"]),
        sources=tuple(ArticleSource(s["name"], s["url"]) for s in data["sources"]),
    )


def article_body_html(article: Article) -> str:
    sections = "".join(
        f"<h2>{escape(s.heading)}</h2>"
        + "".join(f"<p>{escape(p)}</p>" for p in s.paragraphs)
        + (f"<ul>{''.join(f'<li>{escape(p)}</li>' for p in s.points)}</ul>" if s.points else "")
        for s in article.sections
    )
    sources = "".join(f'<li><a href="{escape(s.url)}" rel="nofollow">{escape(s.name)}</a></li>' for s in article.sources)
    return f"{sections}<h2>מקורות</h2><ul>{sources}</ul>"


def article_links_html(articles: tuple[Article, ...]) -> str:
    links = "".join(f'<li><a href="{a.path}">{escape(a.title)}</a> – {escape(a.summary)}</li>' for a in articles)
    return f"<ul>{links}</ul>"


def article_structured_data(article: Article, base_url: str, publisher_name: str) -> dict:
    publisher = {"@type": "Organization", "name": publisher_name, "url": f"{base_url}/"}
    return {
        "@type": "Article", "headline": article.title, "description": article.summary,
        "datePublished": article.published.isoformat(), "inLanguage": "he-IL",
        "mainEntityOfPage": f"{base_url}{article.path}", "author": publisher, "publisher": publisher,
        "citation": [source.url for source in article.sources],
    }
