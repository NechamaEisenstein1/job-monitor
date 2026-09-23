"""Config-driven scrapers. Add a site-specific BaseScraper subclass only when a
site cannot be described by these."""
from __future__ import annotations

import json
from pathlib import Path

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import BaseScraper, ParseError, ScraperConfigError
from backend.infrastructure.scrapers.http import RetryingHttpClient
from backend.infrastructure.scrapers.mapping import extract_items, to_raw_job


class FixtureScraper(BaseScraper):
    """Reads a local JSON list of jobs. Demo / offline development only."""

    def __init__(self, name: str, path: Path):
        self._name = name
        self._path = path

    @property
    def site_name(self) -> str:
        return self._name

    async def fetch_jobs(self) -> list[RawJob]:
        if not self._path.exists():
            raise ScraperConfigError(f"fixture file not found: {self._path}")
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ParseError(f"invalid JSON in {self._path.name}: {exc}") from exc
        return [to_raw_job(item, self._name) for item in extract_items(payload, "")]


class JsonApiScraper(BaseScraper):
    """GETs a JSON endpoint and maps each item with `field_map`."""

    def __init__(self, name: str, url: str, items_path: str, field_map: dict[str, str], http: RetryingHttpClient):
        self._name = name
        self._url = url
        self._items_path = items_path
        self._field_map = field_map
        self._http = http

    @property
    def site_name(self) -> str:
        return self._name

    async def fetch_jobs(self) -> list[RawJob]:
        response = await self._http.get(self._url)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ParseError(f"response from {self._url} is not JSON") from exc
        return [to_raw_job(item, self._name, self._field_map) for item in extract_items(payload, self._items_path)]


class MisconfiguredScraper(BaseScraper):
    """Stands in for a source whose config is invalid, so the problem shows up
    as a CONFIG_ERROR scraper run instead of crashing the whole run."""

    def __init__(self, name: str, reason: str):
        self._name = name
        self._reason = reason

    @property
    def site_name(self) -> str:
        return self._name

    async def fetch_jobs(self) -> list[RawJob]:
        raise ScraperConfigError(self._reason)
