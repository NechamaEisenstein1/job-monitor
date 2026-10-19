"""Experis (Manpower group) - a Next.js site whose job search is client-side GraphQL on
another host. The public sitemap lists every job page (/job/<code>), and each page embeds
the full posting in __NEXT_DATA__ (props.pageProps.job), so no API host is needed."""
from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import ParseError
from backend.infrastructure.scrapers.html import html_to_text, split_requirements
from backend.infrastructure.scrapers.sites.base import SiteScraper

SITEMAP_URL = "https://experis.co.il/sitemap.xml"
_JOB_URL = re.compile(r"<loc>\s*(https://experis\.co\.il/job/(\d+))\s*</loc>")


class ExperisScraper(SiteScraper):
    company = "Experis"

    async def fetch_jobs(self) -> list[RawJob]:
        response = await self._http.get(SITEMAP_URL)
        jobs = self.parse_sitemap(response.text)
        self.require(bool(jobs), "/job/ URLs in sitemap.xml")
        await self._enrich(jobs, self._add_details)
        # The sitemap still lists recently closed jobs; their pages carry no posting (job: null).
        return [j for j in jobs if j.title]

    def parse_sitemap(self, xml: str) -> list[RawJob]:
        return self.dedupe(
            self.job(source_job_id=code, source_url=url, title="") for url, code in _JOB_URL.findall(xml))

    async def _add_details(self, job: RawJob) -> None:
        self.apply_detail(job, await self._html(job.source_url))

    @classmethod
    def apply_detail(cls, job: RawJob, document: BeautifulSoup) -> None:
        data = cls.page_job(document)
        if not data:
            return
        fields = data.get("jobFields") or {}
        job.title = " ".join((data.get("title") or "").split())
        job.description, job.requirements = split_requirements(html_to_text(fields.get("jobdescription")))
        job.location = ", ".join(_names(data, "jobAreas")) or None
        job.employment_type = ", ".join(_names(data, "jobScopes")) or None
        industries = ", ".join(_names(data, "jobIndustries"))
        if industries:
            job.metadata["industry"] = industries

    @staticmethod
    def page_job(document: BeautifulSoup) -> dict[str, Any] | None:
        script = document.find("script", id="__NEXT_DATA__")
        if script is None or not script.string:
            raise ParseError("Experis: job page has no __NEXT_DATA__")
        try:
            return json.loads(script.string)["props"]["pageProps"].get("job")
        except (ValueError, KeyError, TypeError) as exc:
            raise ParseError("Experis: unexpected __NEXT_DATA__ shape") from exc


def _names(data: dict[str, Any], key: str) -> list[str]:
    return [n["name"] for n in ((data.get(key) or {}).get("nodes") or []) if n.get("name")]
