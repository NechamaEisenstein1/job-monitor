"""What search engines get for one indexable page: its <head> data and the crawler text inside #root."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from urllib.parse import quote

from backend.domain.articles import Article

SITE_NAME = "מוניטור משרות"


@dataclass(frozen=True)
class PublicPage:
    path: str
    title: str
    description: str
    priority: str
    # Static text placed inside #root, so crawlers that do not run JavaScript still read the page's
    # heading and main paragraph. React replaces it on mount; it repeats what the page itself shows.
    heading: str = ""
    intro: str = ""
    faq: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    body_html: str = ""                 # more crawler text after the intro, already escaped
    article: Article | None = None      # adds Article structured data
    last_modified: date | None = None   # None: the site-wide date


def absolute_url(base_url: str, path: str) -> str:
    """Article slugs may be Hebrew: URLs in sitemaps and canonical links must be percent-encoded."""
    return base_url + quote(path)
