"""Log-On - b.log-on.com (WordPress). The job search page shows 5 postings and loads the
rest with the "Ajax Load More" plugin; its endpoint (admin-ajax.php?action=alm_get_posts)
returns the same rendered blocks, so the whole board is read with a few large pages.
Each block (div.job) already carries the full posting - no detail requests needed."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.html import soup, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

AJAX_URL = "https://b.log-on.com/wp-admin/admin-ajax.php"
PAGE_SIZE = 100
MAX_PAGES = 30  # ~3,000 postings; far above the board's size, guards against a paging loop
QUERY = {
    # Mirrors the parameters of the search page's .alm-listing element.
    "action": "alm_get_posts", "post_type": "job", "order": "DESC", "orderby": "meta_value",
    "meta_key": "openning_date", "theme_repeater": "jobs-repeater-v2.php", "repeater": "default", "offset": 0,
}
_JOB_URL = re.compile(r"https://b\.log-on\.com/job/[^\s&\"'<>]+")
# ul.info rows are identified by their icon, not their (translatable) label.
_INFO_ICONS = {"fa-anchor": "domain", "fa-history": "experience", "fa-map-marker": "location"}


class LogonScraper(SiteScraper):
    company = "Log-On"

    async def fetch_jobs(self) -> list[RawJob]:
        jobs: list[RawJob] = []
        total = None
        for page in range(MAX_PAGES):
            data = await self._json(AJAX_URL, params={**QUERY, "posts_per_page": PAGE_SIZE, "page": page},
                                    headers={"X-Requested-With": "XMLHttpRequest"})
            self.require(isinstance(data, dict) and "html" in data, "Ajax Load More response (html)")
            meta = data.get("meta") or {}
            total = meta.get("totalposts", total)
            batch = self.parse_page(soup(data["html"]))
            jobs.extend(batch)
            if meta.get("postcount", len(batch)) < PAGE_SIZE:
                break
        self.require(bool(jobs) or total == 0, "job blocks (div.job)")
        return self.dedupe(jobs)

    def parse_page(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for block in document.select("div.job"):
            job = self.parse_block(block)
            if job is None:
                self.skip()
            else:
                jobs.append(job)
        return jobs

    def parse_block(self, block: Tag) -> RawJob | None:
        title = block.select_one(".job-name")
        job_id = block.select_one("[data-job-id]")
        if title is None or job_id is None:
            return None
        info = self._info(block)
        url = self._url(block) or f"https://b.log-on.com/?post_type=job&p={job_id['data-job-id']}"
        requirements = [li.get_text(" ", strip=True) for li in block.select(".list li")]
        if info.get("experience"):
            # "3+" -> "3+ שנות ניסיון", the phrasing the experience parser reads.
            requirements.insert(0, f"{info['experience']} שנות ניסיון")
        return self.job(
            source_job_id=job_id["data-job-id"],
            source_url=url,
            title=title.get_text(" ", strip=True),
            description=text_of(block.select_one(".desc .text")),
            requirements="\n".join(r for r in requirements if r),
            location=info.get("location"),
            domain=info.get("domain"),
            experience=info.get("experience"),
            job_area_id=job_id.get("data-job-area-id"),
            hot=bool(block.select_one("li.hot-job")) or None,
        )

    @staticmethod
    def _info(block: Tag) -> dict[str, str]:
        values = {}
        for li in block.select("ul.info > li"):
            icon = li.select_one("i[class*=fa-]")
            key = next((name for cls, name in _INFO_ICONS.items() if icon and cls in icon.get("class", [])), None)
            label = li.select_one("span")
            if key is None or label is None:
                continue
            label.extract()
            value = li.get_text(" ", strip=True)
            if value:
                values[key] = value
        return values

    @staticmethod
    def _url(block: Tag) -> str | None:
        """The posting's own page, taken from its share links (the block has no direct link)."""
        for link in block.select(".social-links a[href]"):
            found = _JOB_URL.search(link["href"])
            if found:
                return found.group(0)
        return None
