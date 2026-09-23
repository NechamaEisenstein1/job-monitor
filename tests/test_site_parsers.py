"""Offline parser tests against trimmed real pages captured from each site (tests/fixtures/sites).
If a site changes its layout, `python -m backend.cli probe` fails live and these tell you
whether the parser or the site moved."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from backend.domain.services.normalization import normalize_raw_job
from backend.domain.services.validation import validate_job
from backend.infrastructure.scrapers.base import ParseError
from backend.infrastructure.scrapers.html import soup, split_requirements
from backend.infrastructure.scrapers.sites import SITE_SCRAPERS
from backend.infrastructure.scrapers.sites.aman import AmanScraper
from backend.infrastructure.scrapers.sites.comblack import ComblackScraper
from backend.infrastructure.scrapers.sites.consist import ConsistScraper
from backend.infrastructure.scrapers.sites.gav import GavScraper
from backend.infrastructure.scrapers.sites.hms import HmsScraper
from backend.infrastructure.scrapers.sites.horizon import HorizonScraper
from backend.infrastructure.scrapers.sites.matrix import MatrixScraper
from backend.infrastructure.scrapers.sites.ness import NessScraper
from backend.infrastructure.scrapers.sites.one import OneScraper
from backend.infrastructure.scrapers.sites.prologic import PrologicScraper
from backend.infrastructure.scrapers.sites.sqlink import SqlinkScraper
from backend.infrastructure.scrapers.sites.tigbur import TigburScraper
from backend.infrastructure.scrapers.sites.yael import YaelScraper

FIXTURES = Path(__file__).parent / "fixtures" / "sites"


def html(name: str):
    return soup((FIXTURES / f"{name}.html").read_text(encoding="utf-8"))


def data(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def assert_valid(jobs, company: str, *, min_count: int = 2, location: bool = True, requirements: bool = True):
    assert len(jobs) >= min_count
    for raw in jobs:
        job = normalize_raw_job(raw)
        assert validate_job(job) == [], (company, raw)
        assert job.recruitment_company == company
        assert job.source_job_id and job.source_job_id.removeprefix("korn-").isdigit(), raw.source_job_id
        assert job.title and "\n" not in job.title
        if location:
            assert job.location, raw
    if requirements:
        assert any(raw.requirements for raw in jobs), f"{company}: no requirements split"
    assert len({j.source_job_id for j in jobs}) == len(jobs), "duplicate ids"


def test_every_site_scraper_is_registered_with_its_company_name():
    assert len(SITE_SCRAPERS) == 13
    assert len({cls.company for cls in SITE_SCRAPERS.values()}) == 13


def test_matrix():
    jobs = MatrixScraper(None).parse_listing(html("matrix"))
    assert_valid(jobs, "Matrix", min_count=3)
    assert all("/jobs/" in j.source_url for j in jobs)


def test_hms_embedded_json():
    jobs = HmsScraper(None).parse_page(html("hms"))
    assert_valid(jobs, "HMS", min_count=3)


def test_hms_missing_json_is_a_parse_error():
    with pytest.raises(ParseError):
        HmsScraper(None).parse_page(soup("<html><body>redesigned</body></html>"))


def test_tigbur_category_scope():
    everything = TigburScraper(None).parse_payload(data("tigbur"))
    scoped = TigburScraper(None, {"categories": ["הנדסת תוכנה /מחשבים"]}).parse_payload(data("tigbur"))
    assert len(everything) == 3 and len(scoped) == 2
    assert_valid(scoped, "Tigbur", requirements=False)
    assert scoped[0].source_url.startswith("https://tigbur.co.il/new-offer-item/?id=")


def test_aman_listing_and_detail():
    scraper = AmanScraper(None)
    jobs = scraper.parse_listing(html("aman_list"))
    assert_valid(jobs, "Aman", requirements=False)
    scraper.apply_detail(jobs[0], html("aman_detail"))
    assert jobs[0].description and jobs[0].requirements


def test_horizon_listing_and_detail():
    scraper = HorizonScraper(None)
    jobs = scraper.parse_listing(html("horizon_list"))
    assert_valid(jobs, "Horizon", requirements=False)
    scraper.apply_detail(jobs[0], html("horizon_detail"))
    assert jobs[0].requirements
    assert jobs[0].title not in jobs[0].description.splitlines()  # header lines stripped


def test_comblack():
    assert_valid(ComblackScraper(None).parse_listing(html("comblack")), "Comblack", min_count=3)


def test_consist():
    jobs = ConsistScraper(None).parse_listing(html("consist"))
    assert_valid(jobs, "Consist", min_count=3)
    assert jobs[0].source_url == f"https://www.consist.co.il/jobs/?job={jobs[0].source_job_id}"


def test_yael_includes_koren_tech_jobs():
    scraper = YaelScraper(None)
    jobs = scraper.parse_listing(html("yael"))
    assert_valid(jobs, "Yael", min_count=3)
    koren = [j for j in jobs if j.source_job_id.startswith("korn-")]
    assert koren and "/jobs/korn_order/" in koren[0].source_url
    assert not koren[0].title.startswith("(")  # "(16887) ..." reference stripped
    assert scraper.skipped == 0


def test_unreadable_listing_is_counted_not_silently_dropped():
    from backend.application.services.scraper_executor import ScraperExecutor
    from tests.conftest import NOW

    class Broken(YaelScraper):
        async def fetch_jobs(self):
            doc = html("yael")
            doc.select_one("[data-copy]").decompose()  # one listing loses its link
            return self.parse_listing(doc)

    result = asyncio.run(ScraperExecutor(1, lambda: NOW).execute(Broken(None)))
    assert result.warning and "1 listing" in result.warning


def test_gav_api_and_detail():
    scraper = GavScraper(None)
    jobs = scraper.parse_api(data("gav_api"), areas={63: "חיפה והקריות", 41: "ירושלים", 80: 'ירושלים יו"ש'})
    assert_valid(jobs, "GAV Systems", requirements=False, location=False)
    scraper.apply_detail(jobs[0], html("gav_detail"))
    assert jobs[0].description and jobs[0].requirements


def test_ness():
    jobs = NessScraper(None).parse_payload(data("ness"))
    assert_valid(jobs, "Ness", min_count=3)
    assert all("rakaz" not in key for j in jobs for key in j.metadata)  # recruiter PII not kept


def test_ness_unexpected_shape():
    with pytest.raises(ParseError):
        NessScraper(None).parse_payload({"error": "maintenance"})


def test_prologic():
    assert PrologicScraper.parse_categories(html("prologic_index"))
    jobs = PrologicScraper(None).parse_listing(html("prologic_list"), "https://www.prologic.co.il/x")
    assert_valid(jobs, "ProLogic", location=False)


def test_sqlink():
    categories = SqlinkScraper.parse_categories(html("sqlink_index"))
    assert categories and all(c.count("/") == 5 for c in categories)
    assert_valid(SqlinkScraper(None).parse_listing(html("sqlink_list")), "SQLink", location=False)


def test_one():
    jobs = OneScraper(None).parse_items(html("one"))
    assert_valid(jobs, "One")
    assert not any(j.title.endswith(")") for j in jobs)  # internal "(NM123)" refs stripped


@pytest.mark.parametrize("text, expected_req", [
    ("תיאור\nדרישות המשרה:\nPython", "Python"),
    ("תיאור\nדרישות: ניסיון שנה\nSQL", "ניסיון שנה\nSQL"),
    ("desc\n• למי התפקיד יתאים?\nx", "x"),
    ("רק תיאור", ""),
])
def test_split_requirements(text, expected_req):
    assert split_requirements(text)[1] == expected_req


def test_failed_detail_page_keeps_listing_data():
    """One broken detail page must not fail the site."""
    from backend.infrastructure.scrapers.base import NetworkError

    class Flaky(HorizonScraper):
        async def _add_details(self, job):
            raise NetworkError("boom")

    scraper = Flaky(None)
    jobs = scraper.parse_listing(html("horizon_list"))
    asyncio.run(scraper._enrich(jobs, scraper._add_details))
    assert all(j.metadata.get("detail_error") == "boom" for j in jobs)
