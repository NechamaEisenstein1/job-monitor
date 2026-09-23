"""Matrix - WordPress archive of job posts, 10 per page: /jobs/משרה/page/N/ (404 after the last)."""
from __future__ import annotations

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import HttpStatusError
from backend.infrastructure.scrapers.html import first_text, split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

ARCHIVE = "https://www.matrix.co.il/jobs/משרה/"


class MatrixScraper(SiteScraper):
    company = "Matrix"

    async def fetch_jobs(self) -> list[RawJob]:
        jobs: dict[str, RawJob] = {}
        for page in range(1, int(self._options.get("max_pages", 100)) + 1):
            url = ARCHIVE if page == 1 else f"{ARCHIVE}page/{page}/"
            try:
                document = await self._html(url)
            except HttpStatusError as exc:
                if page > 1 and exc.status_code == 404:
                    break  # past the last page
                raise
            page_jobs = self.parse_listing(document)
            if page == 1:
                self.require(bool(page_jobs), "'.job-item' cards on the archive page")
            new = [j for j in page_jobs if j.source_job_id not in jobs]
            if not new:
                break
            jobs.update((j.source_job_id, j) for j in new)
        return list(jobs.values())

    def parse_listing(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for item in document.select(".job-item"):
            # Archive pages use <a class="job-title">, category pages <h2 class="job-title"><a>.
            link = item.select_one("a.job-title, .job-title a")
            if link is None:
                self.skip()
                continue
            body = "\n".join(text_of(p) for p in item.find_all("p", recursive=False) if not p.get("class"))
            more = text_of(item.select_one(".job-more-content"))
            description, requirements = split_requirements(f"{body}\n{more}".strip())
            jobs.append(self.job(
                source_job_id=item.get("job-id") or item.get("id"),
                source_url=link["href"],
                title=link.get_text(" ", strip=True),
                description=description,
                requirements=requirements,
                location=first_text(item, ".job-areas") or None,
            ))
        return jobs
