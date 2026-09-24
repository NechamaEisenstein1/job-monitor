"""Search-engine readiness: only public pages are indexable, private ones never are."""
from __future__ import annotations

from dataclasses import replace
from xml.etree import ElementTree

import pytest

from backend.api.seo import PUBLIC_PAGES, PageRenderer, classify, robots_txt, sitemap_xml
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
    ("/", "public"), ("/login", "public"), ("/privacy", "public"), ("/terms/", "public"),
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
