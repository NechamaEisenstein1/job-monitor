from abc import ABC, abstractmethod

from backend.domain.enums import ScrapeStatus
from backend.domain.models import RawJob


class ScraperError(Exception):
    status: ScrapeStatus = ScrapeStatus.PARSE_ERROR


class ScrapeTimeoutError(ScraperError):
    status = ScrapeStatus.TIMEOUT


class NetworkError(ScraperError):
    status = ScrapeStatus.NETWORK_ERROR


class HttpStatusError(NetworkError):
    def __init__(self, status_code: int, url: str, detail: str | None = None):
        super().__init__(f"HTTP {status_code} for {url}" + (f" ({detail})" if detail else ""))
        self.status_code = status_code


class ParseError(ScraperError):
    """Selector errors, schema mismatch, invalid response structure. Never retried."""
    status = ScrapeStatus.PARSE_ERROR


class ScraperConfigError(ScraperError):
    status = ScrapeStatus.CONFIG_ERROR


class FallbackFailedError(ScraperError):
    """A site's own scraper failed and so did its fallback board. Carries the site's own
    failure status (what needs fixing) and both messages."""

    def __init__(self, primary: ScraperError, fallback_message: str, board: str):
        super().__init__(f"{primary} | fallback {board} also failed: {fallback_message}")
        self.status = primary.status
        self.primary = primary


class BaseScraper(ABC):
    """Site-specific scrapers only map a site's response into RawJob.
    Retry, metrics, run tracking and persistence live elsewhere."""

    @property
    @abstractmethod
    def site_name(self) -> str: ...

    @abstractmethod
    async def fetch_jobs(self) -> list[RawJob]: ...
