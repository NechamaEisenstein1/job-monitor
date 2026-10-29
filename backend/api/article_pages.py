"""The public pages of the guide articles: /articles and /articles/<slug>, built from the database."""
from __future__ import annotations

from html import escape
from urllib.parse import quote

from backend.api.public_page import SITE_NAME, PublicPage, absolute_url
from backend.domain.articles import Article
from backend.domain.services.articles import parse_article_body

ARTICLES_PATH = "/articles"
# Same title and lead as he.ts site.articles, which the page itself shows.
ARTICLES_TITLE = "מדריכים וטיפים לחיפוש עבודה ולמכרזים ממשלתיים"
ARTICLES_LEAD = "עצות מעשיות, עם מקורות, למי שמחפש משרה בהייטק או מתמודד במכרז ממשלתי בתחום התוכנה."


def articles_index_page(articles: list[Article]) -> PublicPage:
    links = "".join(f'<li><a href="{escape(quote(a.path))}">{escape(a.title)}</a> – {escape(a.summary)}</li>'
                    for a in articles)
    return PublicPage(
        ARTICLES_PATH, f"{ARTICLES_TITLE} | {SITE_NAME}",
        "מאמרים מעשיים למתכנתים ולמהנדסי תוכנה: איך ניגשים למכרז ממשלתי, איך פונים למגייסים, "
        "קורות חיים שעוברים סינון, הכנה לראיון ומעקב אחרי הגשה.", "0.8",
        heading=ARTICLES_TITLE, intro=ARTICLES_LEAD, body_html=f"<ul>{links}</ul>",
        last_modified=max((a.updated_at.date() for a in articles), default=None),
    )


def article_page(article: Article) -> PublicPage:
    return PublicPage(article.path, f"{article.title} | {SITE_NAME}", article.summary, "0.7",
                      heading=article.title, intro=article.summary, body_html=_article_body_html(article),
                      article=article, last_modified=article.updated_at.date())


def article_structured_data(article: Article, base_url: str) -> dict:
    publisher = {"@type": "Organization", "name": SITE_NAME, "url": f"{base_url}/"}
    return {
        "@type": "Article", "headline": article.title, "description": article.summary,
        "datePublished": article.published_on.isoformat(), "dateModified": article.updated_at.date().isoformat(),
        "inLanguage": "he-IL", "mainEntityOfPage": absolute_url(base_url, article.path),
        "author": publisher, "publisher": publisher, "citation": [source.url for source in article.sources],
    }


def _article_body_html(article: Article) -> str:
    blocks = "".join(_block_html(block.kind, block.text, block.items) for block in parse_article_body(article.body))
    if not article.sources:
        return blocks
    sources = "".join(f'<li><a href="{escape(s.url)}" rel="nofollow">{escape(s.name)}</a></li>' for s in article.sources)
    return f"{blocks}<h2>מקורות</h2><ul>{sources}</ul>"


def _block_html(kind: str, text: str, items: tuple[str, ...]) -> str:
    if kind == "list":
        return f"<ul>{''.join(f'<li>{escape(item)}</li>' for item in items)}</ul>"
    tag = "h2" if kind == "heading" else "p"
    return f"<{tag}>{escape(text)}</{tag}>"
