"""Search-engine plumbing: per-page <head>, robots.txt, sitemap.xml.

Only the public pages (home, tenders, login, privacy, terms) are indexable. Everything behind
login - and the whole API - is marked noindex and disallowed, so no personal or
member-only content can end up in search results."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
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
    # Static text placed inside #root, so crawlers that do not run JavaScript still read the page's
    # heading and main paragraph. React replaces it on mount; it repeats what the page itself shows.
    heading: str = ""
    intro: str = ""
    faq: tuple[tuple[str, str], ...] = field(default_factory=tuple)


# Questions shown on /tenders (frontend he.ts: tenders.faq) and repeated as FAQPage structured data.
# Keep the two in sync: structured data must match visible text.
TENDERS_FAQ: tuple[tuple[str, str], ...] = (
    ("איזה מכרזים ממשלתיים מופיעים באתר?",
     "מכרזים ומשרות בגופים ממשלתיים בתחומי התכנות והנדסת התוכנה: פיתוח, QA ואוטומציה, DevOps, דאטה, סייבר, "
     "Embedded, IT ומערכות מידע. המכרזים מתפרסמים דרך חברות ההשמה שמאיישות תפקידים במשרדי ממשלה, ברשויות "
     "ובחברות ממשלתיות."),
    ("כל כמה זמן המכרזים מתעדכנים?",
     "האתר סורק כל יום את לוחות המשרות של 14 חברות השמה. מכרזים חדשים נוספים, ומכרזים שהוסרו נמחקים אוטומטית."),
    ("איך מוצאים מכרז שמתאים לניסיון שלי?",
     "בלוח המשרות אפשר לסמן \"מכרזים ממשלתיים בלבד\" ולסנן לפי רמת ניסיון (א', ב' או ג') ולפי אזור מגורים. "
     "מכרזים ממשלתיים מוצגים תמיד ראשונים ומסומנים."),
    ("האם השימוש באתר עולה כסף?",
     "ההרשמה חינם. אחרי ההרשמה מקבלים גישה ללוח המכרזים והמשרות ולהתראות במייל על מכרזים חדשים שמתאימים לפרופיל."),
)

TENDERS_TITLE = "מכרזים ממשלתיים בתכנות ובהנדסת תוכנה"

PUBLIC_PAGES: dict[str, PublicPage] = {p.path: p for p in [
    PublicPage("/", "מכרזים ממשלתיים בתכנות ובהנדסת תוכנה ומשרות הייטק – מוניטור משרות",
               "כל המכרזים הממשלתיים בתחום התכנות והנדסת התוכנה, ולצידם משרות הייטק מ-14 חברות השמה, "
               "מתעדכנים כל יום במקום אחד. מכרזים ממשלתיים בראש הרשימה, סינון לפי רמת ניסיון ואזור, "
               "והתראה במייל על כל מכרז חדש. הרשמה חינם.", "1.0",
               heading="מכרזים ממשלתיים בתכנות ובהנדסת תוכנה – ומשרות הייטק בכל הארץ, במקום אחד",
               intro="מוניטור משרות אוסף כל יום את המכרזים הממשלתיים בתחום התכנות, פיתוח התוכנה והנדסת התוכנה, "
                     "ואת משרות ההייטק מחברות ההשמה המובילות בישראל, ומציג את המכרזים הממשלתיים ראשונים."),
    PublicPage("/tenders", f"{TENDERS_TITLE} – מתעדכן כל יום | {SITE_NAME}",
               "מכרזים ממשלתיים למתכנתים ולמהנדסי תוכנה: פיתוח, QA, DevOps, דאטה, סייבר ו-IT במשרדי ממשלה, "
               "ברשויות ובחברות ממשלתיות. נאספים כל יום מ-14 חברות השמה, עם סינון לפי ניסיון ואזור.", "0.9",
               heading=TENDERS_TITLE,
               intro="כל המכרזים הממשלתיים למתכנתים ולמהנדסי תוכנה במקום אחד: פיתוח, QA ואוטומציה, DevOps, דאטה, "
                     "סייבר ו-IT במשרדי ממשלה, ברשויות ובחברות ממשלתיות. האתר אוסף אותם כל יום מלוחות המשרות "
                     "של חברות ההשמה שמאיישות את המכרזים.",
               faq=TENDERS_FAQ),
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
    r"^/forum/?$", r"^/forum/new/?$", r"^/forum/c/[a-z]+/?$", r"^/forum/t/\d+/?$",
)]
DISALLOWED_PREFIXES = ["/api/", "/me", "/jobs", "/runs", "/sources", "/admin", "/recruiter", "/billing", "/forum"]

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
    tags.append(f'<script type="application/ld+json">{_json_ld(page, base)}</script>')
    if settings.google_site_verification:
        tags.append(f'<meta name="google-site-verification" content="{escape(settings.google_site_verification)}" />')
    return "\n    ".join(tags)


def _json_ld(page: PublicPage, base: str) -> str:
    """schema.org structured data: who the site is, what it offers, and the page's FAQ if it has one."""
    site = {"@type": "WebSite", "@id": f"{base}/#website", "url": f"{base}/", "name": SITE_NAME,
            "inLanguage": "he-IL",
            "description": "מידע על מכרזים ממשלתיים בתחום התכנות והנדסת התוכנה ועל משרות הייטק בישראל"}
    graph: list[dict] = [site, {
        "@type": "WebPage", "@id": f"{base}{page.path}#webpage", "url": base + page.path, "name": page.title,
        "description": page.description, "inLanguage": "he-IL", "isPartOf": {"@id": f"{base}/#website"},
        "about": {"@type": "Thing", "name": TENDERS_TITLE},
    }]
    if page.faq:
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in page.faq
        ]})
    text = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    return text.replace("</", "<\\/")  # never let the data close the <script> element


def body_fallback(path: str) -> str:
    page = PUBLIC_PAGES.get(path if path == "/" else "/" + path.strip("/"))
    if page is None or not page.heading:
        return ""
    faq = "".join(f"<h2>{escape(q)}</h2><p>{escape(a)}</p>" for q, a in page.faq)
    return f"<h1>{escape(page.heading)}</h1><p>{escape(page.intro)}</p>{faq}"


class PageRenderer:
    """Injects per-page head tags (and crawler fallback text in #root) into the built index.html (read once)."""

    def __init__(self, index_html: Path, settings: Settings):
        self._template = index_html.read_text(encoding="utf-8")
        self._settings = settings

    def render(self, path: str) -> str:
        html = _SEO_BLOCK.sub(lambda _: head_tags(path, self._settings), self._template, count=1)
        return html.replace('<div id="root"></div>', f'<div id="root">{body_fallback(path)}</div>', 1)


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
