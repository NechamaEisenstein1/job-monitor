"""Search-engine readiness: only public pages are indexable, private ones never are."""
from __future__ import annotations

from dataclasses import replace
from xml.etree import ElementTree

import json
import re

import pytest

from backend.api.seo import PUBLIC_PAGES, TENDERS_FAQ, PageRenderer, classify, robots_txt, sitemap_xml
from backend.config.settings import PROJECT_ROOT, Settings

TEMPLATE = """<!doctype html><html lang="he"><head>
<!--SEO-->
<title>placeholder</title>
<!--/SEO-->
</head><body><div id="root"></div></body></html>"""


@pytest.fixture
def settings(tmp_path):
    return Settings(database_url="sqlite://", config_dir=PROJECT_ROOT / "config", email_outbox_dir=tmp_path,
                    smtp=None, log_level="WARNING", public_base_url="https://jobs.example.com")


@pytest.fixture
def renderer(tmp_path, settings):
    index = tmp_path / "index.html"
    index.write_text(TEMPLATE, encoding="utf-8")
    return PageRenderer(index, settings)


@pytest.mark.parametrize("path, kind", [
    ("/", "public"), ("/tenders", "public"), ("/login", "public"), ("/privacy", "public"), ("/terms/", "public"),
    ("/me", "private"), ("/jobs", "private"), ("/jobs/123", "private"), ("/admin", "private"),
    ("/runs/2e833407-4d74-4f91-86e1-dbd47b69bc8e", "private"), ("/recruiter", "private"), ("/billing", "private"),
    ("/wp-admin", "unknown"), ("/jobs/abc", "unknown"),
])
def test_page_classification(path, kind):
    assert classify(path) == kind


def test_public_page_head(renderer):
    html = renderer.render("/")
    assert "placeholder" not in html
    assert '<link rel="canonical" href="https://jobs.example.com/" />' in html
    assert '<meta name="robots" content="index, follow" />' in html
    assert '<meta name="description"' in html and "og:title" in html


def test_private_page_is_noindex(renderer):
    html = renderer.render("/me")
    assert 'content="noindex, nofollow"' in html
    assert "canonical" not in html and "description" not in html


def test_search_console_verification_tag(tmp_path, settings):
    index = tmp_path / "index.html"
    index.write_text(TEMPLATE, encoding="utf-8")
    html = PageRenderer(index, replace(settings, google_site_verification="abc123")).render("/")
    assert '<meta name="google-site-verification" content="abc123" />' in html


def test_robots_blocks_private_areas_but_not_public_pages(settings):
    robots = robots_txt(settings)
    for prefix in ("/api/", "/me", "/jobs", "/runs", "/sources", "/admin", "/recruiter", "/billing"):
        assert f"Disallow: {prefix}" in robots
    assert "Disallow: /\n" not in robots and "Allow: /" in robots
    assert "Sitemap: https://jobs.example.com/sitemap.xml" in robots


def test_sitemap_lists_exactly_the_public_pages(settings):
    from datetime import date
    root = ElementTree.fromstring(sitemap_xml(settings, date(2026, 9, 24)))
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in root.findall("s:url/s:loc", ns)]
    assert locs == [f"https://jobs.example.com{p}" for p in PUBLIC_PAGES]


def test_endpoints_and_api_noindex(world):
    client = world.client()
    assert client.get("/robots.txt").headers["content-type"].startswith("text/plain")
    assert client.get("/sitemap.xml").headers["content-type"] == "application/xml"
    assert client.get("/api/auth/config").headers["X-Robots-Tag"] == "noindex, nofollow"


def _json_ld(html: str) -> dict:
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert match, "no structured data"
    return json.loads(match.group(1))


def test_home_page_is_about_government_software_tenders(renderer):
    html = renderer.render("/")
    title = re.search(r"<title>(.*?)</title>", html).group(1)
    assert "מכרזים ממשלתיים" in title and "תוכנה" in title
    # Crawlers that skip JavaScript still see the heading inside #root.
    assert re.search(r'<div id="root"><h1>[^<]*מכרזים ממשלתיים[^<]*</h1>', html)
    graph = _json_ld(html)["@graph"]
    assert {node["@type"] for node in graph} == {"WebSite", "WebPage"}


def test_tenders_page_has_faq_structured_data(renderer):
    html = renderer.render("/tenders")
    faq = next(node for node in _json_ld(html)["@graph"] if node["@type"] == "FAQPage")
    assert [q["name"] for q in faq["mainEntity"]] == [q for q, _ in TENDERS_FAQ]
    assert all(f"<h2>{q}</h2>" in html for q, _ in TENDERS_FAQ)


def test_tenders_faq_matches_the_visible_page():
    """Structured data must repeat what the page shows: the FAQ in he.ts and in seo.py stay identical."""
    he_ts = (PROJECT_ROOT / "frontend" / "src" / "i18n" / "he.ts").read_text(encoding="utf-8")
    block = he_ts[he_ts.index("faq: ["):]
    block = block[:block.index("\n      ],")]
    shown = [(_ts_string(q), _ts_string(a)) for q, a in
             re.findall(r'q: ((?:"(?:[^"\\]|\\.)*"\s*\+?\s*)+),\s*a: ((?:"(?:[^"\\]|\\.)*"\s*\+?\s*)+)\s*}', block)]
    assert shown == list(TENDERS_FAQ)


def _ts_string(expr: str) -> str:
    return "".join(json.loads(part) for part in re.findall(r'"(?:[^"\\]|\\.)*"', expr))


def test_private_page_has_no_fallback_text(renderer):
    assert '<div id="root"></div>' in renderer.render("/me")
