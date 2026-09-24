"""Search-engine plumbing: per-page <head>, robots.txt, sitemap.xml.

Only the public pages (home, login, privacy, terms) are indexable. Everything behind
login - and the whole API - is marked noindex and disallowed, so no personal or
member-only content can end up in search results."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

from backend.config.settings import Settings

SITE_NAME = "מוניטור משרות"


@dataclass(frozen=True)
class PublicPage:
    path: str
    title: str
    description: str
    priority: str


PUBLIC_PAGES: dict[str, PublicPage] = {p.path: p for p in [
    PublicPage("/", "מוניטור משרות – משרות הייטק לג'וניורים בירושלים והסביבה",
               "כל משרות ההייטק מ-14 חברות השמה במקום אחד: סינון משרות ג'וניור (0–2 שנות ניסיון), "
               "סימון מכרזים ממשלתיים, התראות במייל ופנייה אישית למגייסים. הרשמה חינם.", "1.0"),
    PublicPage("/login", f"כניסה והרשמה – {SITE_NAME}",
               "כניסה או הרשמה חינם עם Google או עם אימייל וסיסמה.", "0.5"),
    PublicPage("/privacy", f"מדיניות פרטיות – {SITE_NAME}",
               "איזה מידע נשמר באתר, למה, ואיך מוחקים אותו.", "0.2"),
    PublicPage("/terms", f"תנאי שימוש – {SITE_NAME}", "תנאי השימוש באתר.", "0.2"),
]}

# Pages that exist in the app but require login: served, never indexed.
PRIVATE_PATTERNS = [re.compile(p) for p in (
    r"^/me/?$", r"^/jobs/?$", r"^/jobs/\d+/?$", r"^/runs/?$", r"^/runs/[0-9a-fA-F-]{36}/?$",
    r"^/sources/?$", r"^/admin/?$", r"^/recruiter/?$", r"^/billing/?$",
)]
DISALLOWED_PREFIXES = ["/api/", "/me", "/jobs", "/runs", "/sources", "/admin", "/recruiter", "/billing"]

_SEO_BLOCK = re.compile(r"<!--SEO-->.*?<!--/SEO-->", re.S)


def classify(path: str) -> str:
    """'public' | 'private' | 'unknown' (-> 404)."""
    normalized = path if path == "/" else "/" + path.strip("/")
    if normalized in PUBLIC_PAGES:
        return "public"
    if any(p.match(normalized) for p in PRIVATE_PATTERNS):
        return "private"
    return "unknown"


def head_tags(path: str, settings: Settings) -> str:
    base = settings.public_base_url
    page = PUBLIC_PAGES.get(path if path == "/" else "/" + path.strip("/"))
    if page is None:
        # Private or unknown: a plain title, and an explicit noindex.
        return f'<title>{escape(SITE_NAME)}</title>\n    <meta name="robots" content="noindex, nofollow" />'
    url = base + (page.path if page.path != "/" else "/")
    tags = [
        f"<title>{escape(page.title)}</title>",
        f'<meta name="description" content="{escape(page.description)}" />',
        f'<link rel="canonical" href="{escape(url)}" />',
        '<meta name="robots" content="index, follow" />',
        f'<meta property="og:site_name" content="{escape(SITE_NAME)}" />',
        '<meta property="og:type" content="website" />',
        '<meta property="og:locale" content="he_IL" />',
        f'<meta property="og:title" content="{escape(page.title)}" />',
        f'<meta property="og:description" content="{escape(page.description)}" />',
        f'<meta property="og:url" content="{escape(url)}" />',
        '<meta name="twitter:card" content="summary" />',
    ]
    if settings.google_site_verification:
        tags.append(f'<meta name="google-site-verification" content="{escape(settings.google_site_verification)}" />')
    return "\n    ".join(tags)


class PageRenderer:
    """Injects per-page head tags into the built index.html (read once)."""

    def __init__(self, index_html: Path, settings: Settings):
        self._template = index_html.read_text(encoding="utf-8")
        self._settings = settings

    def render(self, path: str) -> str:
        return _SEO_BLOCK.sub(lambda _: head_tags(path, self._settings), self._template, count=1)


def robots_txt(settings: Settings) -> str:
    lines = ["User-agent: *", "Allow: /"]
    lines += [f"Disallow: {prefix}" for prefix in DISALLOWED_PREFIXES]
    lines += ["", f"Sitemap: {settings.public_base_url}/sitemap.xml", ""]
    return "\n".join(lines)


def sitemap_xml(settings: Settings, last_modified: date) -> str:
    urls = "".join(
        f"  <url><loc>{escape(settings.public_base_url + page.path)}</loc>"
        f"<lastmod>{last_modified.isoformat()}</lastmod><priority>{page.priority}</priority></url>\n"
        for page in PUBLIC_PAGES.values()
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
