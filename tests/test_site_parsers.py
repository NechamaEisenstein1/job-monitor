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
from backend.infrastructure.scrapers.base import HttpStatusError, ParseError
from backend.infrastructure.scrapers.boards import (
    DrushimScraper, FallbackScraper, JobnetScraper, company_url,
)
from backend.infrastructure.scrapers.html import soup, split_requirements
from backend.infrastructure.scrapers.sites import SITE_SCRAPERS
from backend.infrastructure.scrapers.sites.aman import AmanScraper
from backend.infrastructure.scrapers.sites.comblack import ComblackScraper
from backend.infrastructure.scrapers.sites.consist import ConsistScraper
from backend.infrastructure.scrapers.sites.experis import ExperisScraper
from backend.infrastructure.scrapers.sites.gav import GavScraper
from backend.infrastructure.scrapers.sites.hms import HmsScraper
from backend.infrastructure.scrapers.sites.horizon import HorizonScraper
from backend.infrastructure.scrapers.sites.logica import LogicaScraper
from backend.infrastructure.scrapers.sites.logon import LogonScraper
from backend.infrastructure.scrapers.sites.matrix import MatrixScraper
from backend.infrastructure.scrapers.sites.ness import NessScraper
from backend.infrastructure.scrapers.sites.one import OneScraper
from backend.infrastructure.scrapers.sites.prologic import PrologicScraper
from backend.infrastructure.scrapers.sites.sqlink import SqlinkScraper
from backend.infrastructure.scrapers.sites.tigbur import TigburScraper
from backend.infrastructure.scrapers.sites.topsoft import TopSoftScraper
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
    assert len(SITE_SCRAPERS) == 17
    assert len({cls.company for cls in SITE_SCRAPERS.values()}) == 17


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


# ------------------------------------------------------------------ Log-On (b.log-on.com)

def test_logon_ajax_load_more_blocks():
    scraper = LogonScraper(None)
    jobs = scraper.parse_page(soup(data("logon")["html"]))
    assert_valid(jobs, "Log-On", min_count=3)
    assert scraper.skipped == 1  # the block without data-job-id is counted, not dropped silently
    first = jobs[0]
    assert first.source_job_id == "15276"
    assert first.source_url.startswith("https://b.log-on.com/job/")
    assert first.requirements.splitlines()[0] == "3+ שנות ניסיון"  # read by the experience parser
    assert first.metadata["experience"] == "3+" and first.metadata["domain"]


def test_logon_pages_until_a_short_page():
    """100 per request; stops at the first page shorter than that."""
    page = data("logon")

    class Http:
        def __init__(self):
            self.pages = []

        async def request(self, method, url, **kwargs):
            self.pages.append(kwargs["params"]["page"])
            html = page["html"] if kwargs["params"]["page"] == 0 else ""
            count = 100 if kwargs["params"]["page"] == 0 else 0

            class Response:
                @staticmethod
                def json():
                    return {"html": html, "meta": {"postcount": count, "totalposts": 100}}
            return Response()

    http = Http()
    jobs = asyncio.run(LogonScraper(http).fetch_jobs())
    assert http.pages == [0, 1] and len(jobs) == 3


def test_logon_unexpected_response_is_a_parse_error():
    class Http:
        async def request(self, method, url, **kwargs):
            class Response:
                @staticmethod
                def json():
                    return 0  # WordPress answers "0" for an unknown admin-ajax action
            return Response()

    with pytest.raises(ParseError):
        asyncio.run(LogonScraper(Http()).fetch_jobs())


# ------------------------------------------------------------------ Logica, Experis, Top Soft

def test_logica_listing_and_detail():
    scraper = LogicaScraper(None)
    jobs = scraper.parse_listing(html("logica_list"))
    assert_valid(jobs, "Logica", min_count=3, requirements=False)
    assert all(j.source_url == f"https://logica-it.com/jobs/{j.source_job_id}/" for j in jobs)
    assert all(j.metadata["category"] for j in jobs)
    scraper.apply_detail(jobs[0], html("logica_detail"))
    assert jobs[0].description and "Firewall" in jobs[0].requirements


def test_experis_sitemap_and_job_page():
    scraper = ExperisScraper(None)
    jobs = scraper.parse_sitemap((FIXTURES / "experis_sitemap.xml").read_text(encoding="utf-8"))
    assert [j.source_job_id for j in jobs] == ["244605", "244592", "244588"]  # articles ignored
    job = jobs[0]
    scraper.apply_detail(job, html("experis_job"))
    assert_valid([job], "Experis", min_count=1)
    assert job.location == "תל אביב והמרכז, שרון, שפלה" and job.employment_type == "משרה מלאה"


def test_experis_closed_job_page_is_dropped():
    job = ExperisScraper(None).parse_sitemap("<loc>https://experis.co.il/job/1</loc>")[0]
    ExperisScraper.apply_detail(job, soup(
        '<script id="__NEXT_DATA__">{"props": {"pageProps": {"job": null}}}</script>'))
    assert job.title == ""
    with pytest.raises(ParseError):
        ExperisScraper.apply_detail(job, soup("<html>redesigned</html>"))


def test_topsoft_api_and_detail():
    scraper = TopSoftScraper(None)
    jobs = scraper.parse_api(data("topsoft_api"), locations={76: "בני ברק", 93: "יקום", 46: "שרון"})
    assert_valid(jobs, "Top Soft", min_count=3, requirements=False, location=False)
    assert jobs[0].title == "Umbraco Training & Implementation Specialist"  # entities decoded
    scraper.apply_detail(jobs[0], html("topsoft_detail"))
    assert jobs[0].description and "Umbraco" in jobs[0].requirements
    assert jobs[0].metadata["job_number"] == "8847"


# ------------------------------------------------------------------ job boards (Drushim, JobNet)

def test_drushim_company_page_and_job_page():
    scraper = DrushimScraper("Binat Samech", ["16583-בינת-סמך"], None)
    jobs = scraper.parse_company(html("drushim_company"))
    assert_valid(jobs, "Binat Samech", min_count=3, requirements=False)
    assert all(j.source_url.startswith("https://www.drushim.co.il/job/") for j in jobs)
    job = next(j for j in jobs if j.source_job_id == "38729223")
    scraper.apply_detail(job, html("drushim_job"))
    assert job.requirements and "\n" in job.description
    assert company_url("16583-בינת-סמך") == "https://www.drushim.co.il/%D7%93%D7%A8%D7%95%D7%A9%D7%99%D7%9D-16583-%D7%91%D7%99%D7%A0%D7%AA-%D7%A1%D7%9E%D7%9A/"


def test_drushim_page_without_profile_is_a_parse_error():
    with pytest.raises(ParseError):
        DrushimScraper("X", ["1-x"], None).parse_company(soup("<html><body>404</body></html>"))


def test_jobnet_company_page():
    jobs = JobnetScraper("Malam Team", ["20997"], None).parse_page(html("jobnet_company"))
    assert_valid(jobs, "Malam Team", min_count=3)
    first = jobs[0]
    assert first.source_url == "https://www.jobnet.co.il/jobs?positionid=12831148"
    assert not first.description.startswith("תיאור תפקיד") and not first.requirements.startswith("דרישות")
    assert first.employment_type == "משרה מלאה" and first.published_at.year == 2026


def test_jobnet_pages_until_a_short_page():
    page = (FIXTURES / "jobnet_company.html").read_text(encoding="utf-8")
    full = page.replace("<body>", "<body>" + "".join(
        f'<div class="inerbox"><a href="/jobs?positionid={9000 + i}"><h2 itemprop="title">Job {i}</h2></a></div>'
        for i in range(12)))

    class Http:
        def __init__(self):
            self.calls = []

        async def get(self, url, **kwargs):
            self.calls.append((kwargs["params"]["companyID"], kwargs["params"]["p"]))

            class Response:
                text = full if kwargs["params"]["p"] == 0 else page
            return Response()

    http = Http()
    jobs = asyncio.run(JobnetScraper("Malam Team", ["1", "2"], http).fetch_jobs())
    assert http.calls == [("1", 0), ("1", 1), ("2", 0), ("2", 1)]
    assert len(jobs) == 15  # same postings on both companies' pages are kept once


def test_board_sources_and_fallback_are_built_from_config():
    from backend.config.settings import SourceConfig
    from backend.infrastructure.scrapers.registry import build_scraper

    board = build_scraper(SourceConfig("Unilink", "drushim", {"pages": ["8275-יונילינק"]}), None)
    assert isinstance(board, DrushimScraper) and board.site_name == "Unilink"
    wrapped = build_scraper(SourceConfig("Aman", "site", {
        "site": "aman", "fallback": {"type": "jobnet", "pages": ["1"]}}), None)
    assert isinstance(wrapped, FallbackScraper) and wrapped.site_name == "Aman"
    assert isinstance(wrapped.fallback, JobnetScraper) and wrapped.fallback.company == "Aman"


def test_every_configured_source_builds():
    from backend.config.settings import PROJECT_ROOT, load_sources_config
    from backend.infrastructure.scrapers.generic import MisconfiguredScraper
    from backend.infrastructure.scrapers.registry import build_scrapers

    scrapers = build_scrapers(load_sources_config(PROJECT_ROOT / "config"), None)
    assert not [s.site_name for s in scrapers if isinstance(s, MisconfiguredScraper)]
    names = [s.site_name for s in scrapers]
    assert len(names) == len(set(names)), "source names must be unique (run tracking is per name)"


@pytest.mark.parametrize("error, falls_back", [
    (HttpStatusError(403, "https://x", "Cloudflare challenge"), True),
    (ParseError("layout changed"), False),
])
def test_fallback_only_when_the_site_refuses(error, falls_back):
    class Blocked(AmanScraper):
        async def fetch_jobs(self):
            raise error

    class Board(DrushimScraper):
        async def fetch_jobs(self):
            return self.parse_company(html("drushim_company"))

    scraper = FallbackScraper(Blocked(None), Board("Aman", ["1-x"], None))
    if falls_back:
        jobs = asyncio.run(scraper.fetch_jobs())
        assert len(jobs) == 3 and scraper.used_fallback
        assert {j.recruitment_company for j in jobs} == {"Aman"}
    else:
        with pytest.raises(ParseError):
            asyncio.run(scraper.fetch_jobs())
