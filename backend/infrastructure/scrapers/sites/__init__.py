"""Per-site scrapers, keyed by the `site:` value used in config/sources.yaml."""
from backend.infrastructure.scrapers.sites.aman import AmanScraper
from backend.infrastructure.scrapers.sites.base import SiteScraper
from backend.infrastructure.scrapers.sites.comblack import ComblackScraper
from backend.infrastructure.scrapers.sites.consist import ConsistScraper
from backend.infrastructure.scrapers.sites.gav import GavScraper
from backend.infrastructure.scrapers.sites.hms import HmsScraper
from backend.infrastructure.scrapers.sites.horizon import HorizonScraper
from backend.infrastructure.scrapers.sites.logon import LogonScraper
from backend.infrastructure.scrapers.sites.matrix import MatrixScraper
from backend.infrastructure.scrapers.sites.ness import NessScraper
from backend.infrastructure.scrapers.sites.one import OneScraper
from backend.infrastructure.scrapers.sites.prologic import PrologicScraper
from backend.infrastructure.scrapers.sites.sqlink import SqlinkScraper
from backend.infrastructure.scrapers.sites.tigbur import TigburScraper
from backend.infrastructure.scrapers.sites.yael import YaelScraper

SITE_SCRAPERS: dict[str, type[SiteScraper]] = {
    "matrix": MatrixScraper,
    "hms": HmsScraper,
    "tigbur": TigburScraper,
    "aman": AmanScraper,
    "horizon": HorizonScraper,
    "comblack": ComblackScraper,
    "consist": ConsistScraper,
    "yael": YaelScraper,
    "gav": GavScraper,
    "ness": NessScraper,
    "prologic": PrologicScraper,
    "sqlink": SqlinkScraper,
    "one": OneScraper,
    "logon": LogonScraper,
}
