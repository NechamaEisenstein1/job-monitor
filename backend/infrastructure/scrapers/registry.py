from __future__ import annotations

from pathlib import Path

from backend.config.settings import PROJECT_ROOT, SourceConfig
from backend.infrastructure.scrapers.base import BaseScraper
from backend.infrastructure.scrapers.boards import DrushimScraper, FallbackScraper, JobnetScraper
from backend.infrastructure.scrapers.generic import FixtureScraper, JsonApiScraper, MisconfiguredScraper
from backend.infrastructure.scrapers.http import RetryingHttpClient
from backend.infrastructure.scrapers.sites import SITE_SCRAPERS


BOARD_SCRAPERS = {"drushim": DrushimScraper, "jobnet": JobnetScraper}


def build_scraper(source: SourceConfig, http: RetryingHttpClient) -> BaseScraper:
    opts = source.options
    try:
        if source.type in BOARD_SCRAPERS:
            return BOARD_SCRAPERS[source.type](source.name, list(opts["pages"]), http, opts)
        if source.type == "site":
            cls = SITE_SCRAPERS.get(opts["site"])
            if cls is None:
                return MisconfiguredScraper(source.name, f"unknown site '{opts['site']}'")
            if cls.company != source.name:
                return MisconfiguredScraper(
                    source.name, f"source name must be '{cls.company}' for site '{opts['site']}'")
            scraper = cls(http, opts)
            fallback = opts.get("fallback")
            if fallback:
                board = BOARD_SCRAPERS.get(fallback.get("type"))
                if board is None:
                    return MisconfiguredScraper(source.name, f"unknown fallback type '{fallback.get('type')}'")
                return FallbackScraper(scraper, board(source.name, list(fallback["pages"]), http, fallback))
            return scraper
        if source.type == "fixture":
            path = Path(opts["path"])
            return FixtureScraper(source.name, path if path.is_absolute() else PROJECT_ROOT / path)
        if source.type == "json_api":
            return JsonApiScraper(source.name, opts["url"], opts.get("items_path", ""), opts["field_map"], http)
    except KeyError as exc:
        return MisconfiguredScraper(source.name, f"missing option {exc} for source type '{source.type}'")
    return MisconfiguredScraper(source.name, f"unknown source type '{source.type}'")


def is_enabled(source: SourceConfig) -> bool:
    return bool(source.options.get("enabled", True))


def build_scrapers(sources: list[SourceConfig], http: RetryingHttpClient) -> list[BaseScraper]:
    return [build_scraper(s, http) for s in sources if is_enabled(s)]
