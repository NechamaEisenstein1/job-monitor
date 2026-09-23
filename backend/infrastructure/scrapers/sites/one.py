"""One Technologies (incl. Taldor) - /careers/ renders the first 10 jobs; further pages come
from admin-ajax `load_more_jobs` (POST, returns more .accordion_item HTML, empty at the end)."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.html import soup, split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

CAREERS_URL = "https://www.one1.co.il/careers/"
AJAX_URL = "https://www.one1.co.il/wp-admin/admin-ajax.php?lang=he"
JOB_URL = "https://www.one1.co.il/?share_job_id={id}"
# Internal recruiter refs appended to titles: "(NM27673)", "(AK 24326)", "[VM 24917]".
_REF = re.compile(r"\s*[(\[]\s*[A-Za-z]{0,3}\s*\d+\s*[)\]]\s*$")


class OneScraper(SiteScraper):
    company = "One"

    async def fetch_jobs(self) -> list[RawJob]:
        first = await self._html(CAREERS_URL)
        jobs = self.parse_items(first)
        self.require(bool(jobs), "'.accordion_item' jobs")
        button = first.select_one("#load-more-jobs")
        last_page = int(button.get("data-max", 1)) if button else 1
        for page in range(2, min(last_page, int(self._options.get("max_pages", 60))) + 1):
            response = await self._http.post(
                AJAX_URL, data={"action": "load_more_jobs", "page": page, "career_page_link": CAREERS_URL},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            page_jobs = self.parse_items(soup(response.text))
            if not page_jobs:
                break
            jobs.extend(page_jobs)
        return self.dedupe(jobs)

    def parse_items(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for item in document.select(".accordion_item[data-id]"):
            title = item.select_one(".job_title")
            if title is None:
                self.skip()
                continue
            tags = {img.get("alt", ""): li.get_text(" ", strip=True)
                    for li in item.select(".career-tag-list li") if (img := li.find("img"))}
            content = item.select_one(".accordion_content")
            for noise in content.select(".accordion_content_img, form, .share-links, script, style") if content else []:
                noise.decompose()
            description, requirements = split_requirements(text_of(content))
            jobs.append(self.job(
                source_job_id=item["data-id"],
                source_url=JOB_URL.format(id=item["data-id"]),
                title=_REF.sub("", title.get_text(" ", strip=True)),
                description=description,
                requirements=requirements,
                location=tags.get("מיקום משרה"),
                employment_type=tags.get("סוג משרה"),
            ))
        return jobs
