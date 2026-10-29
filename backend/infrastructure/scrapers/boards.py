"""Job boards read per recruitment company: Drushim and JobNet company pages.

A board source lists the board's pages of ONE recruitment company (sometimes several pages,
e.g. a group's divisions), so every job is recorded under that company - the source's name.
Used on its own for companies without a usable site of their own, and as the fallback of a
site scraper that the company's site refuses (see FallbackScraper)."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote

from bs4 import BeautifulSoup, Tag

from backend.domain.models import RawJob
from backend.domain.services.scraper_health import FailureKind, classify, fallback_note
from backend.infrastructure.scrapers.base import BaseScraper, FallbackFailedError, ParseError, ScraperError
from backend.infrastructure.scrapers.html import split_requirements, text_of
from backend.infrastructure.scrapers.http import RetryingHttpClient
from backend.infrastructure.scrapers.sites.base import SiteScraper
from backend.observability import log_event


class BoardScraper(SiteScraper):
    """A SiteScraper whose company comes from the source config instead of the class."""

    def __init__(self, company: str, pages: list[str], http: RetryingHttpClient | None,
                 options: dict[str, Any] | None = None):
        super().__init__(http, options)
        self.company = company
        self._pages = [str(p).strip() for p in pages if str(p).strip()]


# ---------------------------------------------------------------------------- Drushim

DRUSHIM = "https://www.drushim.co.il"


class DrushimScraper(BoardScraper):
    """Company page /דרושים-<id>-<slug>/ (Next.js) embeds every open job of the company in
    __NEXT_DATA__ (props.pageProps.profile.jobs); each job page adds the description and
    requirements as separate line lists. `pages` are the "<id>-<slug>" parts of the URLs."""

    board_name = "Drushim"

    async def fetch_jobs(self) -> list[RawJob]:
        jobs: list[RawJob] = []
        for page in self._pages:
            jobs.extend(self.parse_company(await self._html(company_url(page))))
        jobs = self.dedupe(jobs)
        await self._enrich(jobs, self._add_details)
        return jobs

    def parse_company(self, document: BeautifulSoup) -> list[RawJob]:
        props = next_data(document, self.company)
        profile = props.get("profile")
        self.require(isinstance(profile, dict) and isinstance(profile.get("jobs"), list),
                     "Drushim company profile (pageProps.profile.jobs)")
        jobs = []
        for item in profile["jobs"]:
            if not item.get("id") or not item.get("title") or not item.get("jobUrl"):
                self.skip()
                continue
            jobs.append(self.job(
                source_job_id=item["id"],
                source_url=DRUSHIM + item["jobUrl"],
                title=" ".join(item["title"].split()),
                description=item.get("description") or "",
                location=", ".join(item.get("cities") or []) or item.get("city") or None,
                employment_type=", ".join(item.get("scopes") or []) or item.get("scope") or None,
                published_at=_iso(item.get("publishedAtIso")),
                board="drushim",
                board_company=item.get("companyName"),
                experience=item.get("experience"),
            ))
        return jobs

    async def _add_details(self, job: RawJob) -> None:
        self.apply_detail(job, await self._html(job.source_url))

    def apply_detail(self, job: RawJob, document: BeautifulSoup) -> None:
        data = next_data(document, self.company).get("job")
        if not isinstance(data, dict):
            return
        description = "\n".join(data.get("description") or [])
        requirements = "\n".join(data.get("requirements") or [])
        if description:
            job.description = description
        if requirements:
            job.requirements = requirements
        categories = ", ".join(c["name"] for c in data.get("categories") or [] if c.get("name"))
        if categories:
            job.metadata["category"] = categories


def company_url(page: str) -> str:
    return f"{DRUSHIM}/{quote(f'דרושים-{page}')}/"


def next_data(document: BeautifulSoup, company: str) -> dict[str, Any]:
    script = document.find("script", id="__NEXT_DATA__")
    if script is None or not script.string:
        raise ParseError(f"{company}: Drushim page has no __NEXT_DATA__ - site layout may have changed")
    try:
        props = json.loads(script.string)["props"]["pageProps"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ParseError(f"{company}: unexpected Drushim __NEXT_DATA__ shape") from exc
    return props if isinstance(props, dict) else {}


# ---------------------------------------------------------------------------- JobNet

JOBNET = "https://www.jobnet.co.il"
_POSITION_ID = re.compile(r"positionid=(\d+)", re.IGNORECASE)
MAX_JOBNET_PAGES = 30  # 15 jobs a page; guards against a paging loop


class JobnetScraper(BoardScraper):
    """Company page /Company?companyID=N (ASP.NET) shows 15 full postings a page
    (schema.org JobPosting microdata); `p=` (0-based) pages through them until one is empty.
    `pages` are JobNet companyIDs."""

    board_name = "JobNet"

    async def fetch_jobs(self) -> list[RawJob]:
        jobs: list[RawJob] = []
        for company_id in self._pages:
            for page in range(MAX_JOBNET_PAGES):
                document = await self._html(f"{JOBNET}/Company", params={"p": page, "companyID": company_id})
                batch = self.parse_page(document)
                jobs.extend(batch)
                if len(batch) < 15:
                    break
        return self.dedupe(jobs)

    def parse_page(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for box in document.select("div.inerbox"):
            job = self.parse_box(box)
            if job is None:
                self.skip()
            else:
                jobs.append(job)
        return jobs

    def parse_box(self, box: Tag) -> RawJob | None:
        link = box.select_one("a[href*='positionid=']")
        title = box.select_one("[itemprop=title]")
        match = _POSITION_ID.search(link["href"]) if link else None
        if match is None or title is None or not title.get_text(strip=True):
            return None
        description = _drop_heading(text_of(box.select_one("[itemprop=description]")), "תיאור תפקיד")
        requirements = _drop_heading(text_of(box.select_one("[itemprop=skills]")), "דרישות")
        if not requirements:
            description, requirements = split_requirements(description)
        locations = [" ".join(loc.get_text(" ", strip=True).split()) for loc in box.select("[itemprop=jobLocation]")]
        employer = box.select_one("[itemprop=hiringOrganization]")
        employment = box.select_one("[itemprop=employmentType]")
        return self.job(
            source_job_id=match.group(1),
            source_url=f"{JOBNET}/jobs?positionid={match.group(1)}",
            title=" ".join(title.get_text(" ", strip=True).split()),
            description=description,
            requirements=requirements,
            location="; ".join(filter(None, locations)) or None,
            employment_type=employment.get_text(" ", strip=True) if employment else None,
            published_at=_dmy(box.select_one("[itemprop=datePosted]")),
            board="jobnet",
            board_company=employer.get_text(" ", strip=True) if employer else None,
        )


def _drop_heading(text: str, heading: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip().rstrip(":").strip() == heading:
        lines = lines[1:]
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------- fallback

class FallbackScraper(BaseScraper):
    """Runs a company's own-site scraper and, whenever that fails - the site refuses us
    (HTTP error, network failure, timeout, e.g. a Cloudflare challenge), its layout changed
    (parse error) or it suddenly lists nothing - collects the same company from a job board.

    Using the board is never silent: `note` holds a warning naming the own-site failure and
    its kind, recorded on the run, so a broken own-site scraper is still reported (see
    domain/services/scraper_health.py) while the jobs keep flowing."""

    def __init__(self, primary: BaseScraper, fallback: BaseScraper):
        self.primary = primary
        self.fallback = fallback
        self.skipped = 0
        self.used_fallback = False
        self.note: str | None = None

    @property
    def site_name(self) -> str:
        return self.primary.site_name

    @property
    def board_name(self) -> str:
        return getattr(self.fallback, "board_name", type(self.fallback).__name__)

    async def fetch_jobs(self) -> list[RawJob]:
        self.used_fallback, self.note = False, None
        for scraper in (self.primary, self.fallback):
            if hasattr(scraper, "skipped"):
                scraper.skipped = 0
        try:
            jobs = await self.primary.fetch_jobs()
        except ScraperError as exc:
            failure: ScraperError = exc
        else:
            if jobs:
                self.skipped = getattr(self.primary, "skipped", 0)
                return jobs
            failure = ParseError(f"{self.site_name}: own site returned zero jobs")

        kind = classify(failure.status, str(failure)) or FailureKind.TEMPORARY
        log_event("site_fallback", logging.WARNING, site=self.site_name, kind=kind.value,
                  board=self.board_name, error=str(failure)[:200])
        self.used_fallback = True
        try:
            jobs = await self.fallback.fetch_jobs()
        except ScraperError as exc:
            raise FallbackFailedError(failure, str(exc), self.board_name) from exc
        self.skipped = getattr(self.fallback, "skipped", 0)
        if jobs:
            self.note = fallback_note(kind, str(failure), self.board_name)
        elif isinstance(failure, ParseError) and "zero jobs" in str(failure):
            return []  # the company lists nothing anywhere: a genuine zero, reported as such
        else:
            raise FallbackFailedError(failure, "board returned zero jobs", self.board_name)
        return jobs


def _iso(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def _dmy(node: Tag | None) -> datetime | None:
    try:
        return datetime.strptime(node.get_text(strip=True), "%d/%m/%Y") if node else None
    except ValueError:
        return None
