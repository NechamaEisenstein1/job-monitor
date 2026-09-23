"""ProLogic - /High-tech-jobs links to ~50 sub-category pages; each lists its jobs
(.allJobsDIV). A job can appear under several categories, so results are de-duplicated."""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.html import first_text, split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

INDEX_URL = "https://www.prologic.co.il/High-tech-jobs"


class PrologicScraper(SiteScraper):
    company = "ProLogic"

    async def fetch_jobs(self) -> list[RawJob]:
        categories = self.parse_categories(await self._html(INDEX_URL))
        self.require(bool(categories), "sub-category links (a.allJobsSubCategoriesDIVA)")
        jobs: list[RawJob] = []
        for url in categories:
            jobs.extend(self.parse_listing(await self._html(url), url))
        return self.dedupe(jobs)

    @staticmethod
    def parse_categories(document: BeautifulSoup) -> list[str]:
        links = (urljoin(INDEX_URL, a["href"]) for a in document.select("a.allJobsSubCategoriesDIVA[href]"))
        return list(dict.fromkeys(links))

    def parse_listing(self, document: BeautifulSoup, page_url: str) -> list[RawJob]:
        jobs = []
        for block in document.select(".allJobsDIV"):
            link = block.select_one("a[href]")
            cms_id = block.select_one("input[name=cmsId]")
            if link is None or cms_id is None:
                self.skip()
                continue
            description, requirements = split_requirements(text_of(block.select_one(".allJobsDescription")))
            jobs.append(self.job(
                source_job_id=cms_id.get("value"),
                source_url=urljoin(page_url, link["href"]),
                title=first_text(block, ".allJobsTitle"),
                description=description,
                requirements=requirements,
            ))
        return jobs
