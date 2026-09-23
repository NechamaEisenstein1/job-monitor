from collections.abc import Sequence

from backend.config.settings import RunStatusConfig
from backend.domain.enums import RunStatus, ScrapeStatus
from backend.domain.models import ScraperRun


def compute_run_status(scraper_runs: Sequence[ScraperRun], cfg: RunStatusConfig) -> RunStatus:
    if not scraper_runs:
        return RunStatus.FAILED  # zero configured scrapers is a configuration failure

    successful = sum(1 for run in scraper_runs if run.status == ScrapeStatus.SUCCESS)
    ratio = successful / len(scraper_runs)

    if ratio >= cfg.success_ratio:
        return RunStatus.SUCCESS
    if ratio >= cfg.partial_ratio:
        return RunStatus.PARTIAL
    return RunStatus.FAILED
