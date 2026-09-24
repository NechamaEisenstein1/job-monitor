"""Honesty labels: new / ghost (long-open or re-published), several agencies, fake junior."""
from __future__ import annotations

import asyncio
import json
from datetime import timedelta

from backend.application.services.notification import NotificationService
from backend.application.services.scraper_executor import ScraperExecutor
from backend.application.use_cases.run_pipeline import RunPipeline
from backend.config.settings import SignalsConfig
from backend.domain.models import PostingHistory
from backend.domain.services.evaluation import JobEvaluationService
from backend.domain.services.signals import SignalPolicy
from backend.infrastructure.repositories.read_models import SqlReadRepository
from backend.infrastructure.repositories.sql import SqlNotificationRepository, SqlUnitOfWork
from backend.infrastructure.scrapers.generic import FixtureScraper
from tests.conftest import NOW, make_job


def _history(company="Matrix", first=NOW, reposts=0) -> PostingHistory:
    return PostingHistory(id=None, recruitment_company=company, posting_key="id:1", title_key="t",
                          first_seen_at=first, origin_first_seen_at=first, last_seen_at=NOW, reposts=reposts)


# ------------------------------------------------------------------ policy

def test_new_ghost_and_agencies():
    policy = SignalPolicy(SignalsConfig(new_within_hours=30, ghost_after_days=45, ghost_min_reposts=2))
    fresh = policy.compute([_history(first=NOW - timedelta(hours=5))], NOW)
    assert fresh.is_new and not fresh.is_ghost and fresh.days_open == 0

    old = policy.compute([_history(first=NOW - timedelta(days=60))], NOW)
    assert old.is_ghost and not old.is_new and old.days_open == 60

    reposted = policy.compute([_history(first=NOW - timedelta(hours=2), reposts=2)], NOW)
    assert reposted.is_ghost and not reposted.is_new  # re-published is never "new"

    several = policy.compute([_history("HMS", NOW - timedelta(days=3)), _history("Matrix", NOW - timedelta(days=9))], NOW)
    assert several.agency_count == 2 and several.first_agency == "Matrix" and several.days_open == 9
    assert policy.compute([], NOW).agency_count == 0


# ------------------------------------------------------------------ fake junior

def test_fake_junior_flag(cfg):
    evaluator = JobEvaluationService.from_config(cfg)
    fake = evaluator.evaluate(make_job(title="מפתח/ת Java ג'וניור", requirements="ניסיון של 4 שנים לפחות"), "r", NOW)
    assert fake.junior_title_mismatch and fake.required_years == 4 and not fake.is_junior
    honest = evaluator.evaluate(make_job(title="Junior Python Developer", requirements="1+ years of experience"), "r", NOW)
    assert not honest.junior_title_mismatch and honest.is_junior
    senior = evaluator.evaluate(make_job(title="Senior Java Developer", requirements="5 years of experience"), "r", NOW)
    assert not senior.junior_title_mismatch  # never claimed to be junior


# ------------------------------------------------------------------ pipeline history

def _posting(i: int, title: str | None = None) -> dict:
    return {"source_job_id": f"M-{i}", "source_url": f"https://matrix.example.com/jobs/{i}",
            "title": title or f"Backend Developer {i}", "client_company": f"Client {i}", "location": "Jerusalem",
            "description": "Python services.", "requirements": "Python"}


def _run(session_factory, cfg, tmp_path, day: int, postings: dict[str, list[dict]]):
    scrapers = []
    for company, items in postings.items():
        path = tmp_path / f"{company}-{day}.json"
        path.write_text(json.dumps(items), encoding="utf-8")
        scrapers.append(FixtureScraper(company, path))
    now = NOW + timedelta(days=day)

    class Sender:
        def send(self, *_):
            pass

    with session_factory() as s, session_factory() as ns:
        asyncio.run(RunPipeline(
            SqlUnitOfWork(s), scrapers, ScraperExecutor(2, lambda: now), cfg, JobEvaluationService.from_config(cfg),
            NotificationService(SqlNotificationRepository(ns), Sender(), cfg.email, lambda: now), lambda: now,
        ).run())


def _by_title(session_factory, title: str):
    with session_factory() as s:
        return next(i for i in SqlReadRepository(s).list_jobs(q=title, page_size=100).items if i.title == title)


def test_republished_posting_keeps_its_age_and_counts_reposts(session_factory, cfg, tmp_path):
    base = [_posting(i) for i in range(1, 5)]
    _run(session_factory, cfg, tmp_path, 0, {"Matrix": base})
    _run(session_factory, cfg, tmp_path, 1, {"Matrix": base[:3]})            # posting 4 taken down
    _run(session_factory, cfg, tmp_path, 5, {"Matrix": base[:3] + [_posting(9, "Backend Developer 4")]})  # new id

    job = _by_title(session_factory, "Backend Developer 4")
    assert job.signals.reposts == 1
    assert job.signals.open_since.replace(tzinfo=None) == NOW  # original first sighting, not day 5
    assert not job.signals.is_new

    # Same id taken down and back again: counted too.
    _run(session_factory, cfg, tmp_path, 6, {"Matrix": base[:3]})
    _run(session_factory, cfg, tmp_path, 7, {"Matrix": base[:3] + [_posting(9, "Backend Developer 4")]})
    assert _by_title(session_factory, "Backend Developer 4").signals.reposts == 2
    assert _by_title(session_factory, "Backend Developer 4").signals.is_ghost  # ghost_min_reposts = 2


def test_same_job_at_several_agencies_names_the_first(session_factory, cfg, tmp_path):
    shared = {"title": "Junior QA Engineer", "client_company": "Intel", "location": "Jerusalem",
              "description": "Manual and automated testing.", "requirements": "Python"}
    _run(session_factory, cfg, tmp_path, 0, {"Matrix": [{**shared, "source_job_id": "M-1",
                                                         "source_url": "https://m.example.com/1"}]})
    _run(session_factory, cfg, tmp_path, 2, {
        "Matrix": [{**shared, "source_job_id": "M-1", "source_url": "https://m.example.com/1"}],
        "HMS": [{**shared, "source_job_id": "H-7", "source_url": "https://h.example.com/7"}],
    })
    job = _by_title(session_factory, "Junior QA Engineer")
    assert job.signals.agency_count == 2 and job.signals.first_agency == "Matrix"
    assert job.source_count == 2


def test_api_exposes_signals_and_fake_junior(world):
    items = world.client("junior@example.com").get("/api/jobs", params={"page_size": 100}).json()["items"]
    assert items and all(i["signals"] and i["signals"]["agency_count"] >= 1 for i in items)
    detail = world.client("junior@example.com").get(f"/api/jobs/{items[0]['id']}").json()
    assert detail["signals"]["open_since"] and "junior_title_mismatch" in detail["evaluation"]


def test_migration_seeds_history_from_existing_postings(tmp_path):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from backend.config.settings import PROJECT_ROOT

    url = f"sqlite:///{tmp_path / 'm.db'}"
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "backend/infrastructure/db/migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    alembic_cfg.attributes["configure_logger"] = False
    command.upgrade(alembic_cfg, "0004")
    engine = create_engine(url)
    with engine.begin() as c:
        c.execute(text("INSERT INTO scrape_runs (id, scheduled_date, started_at, status, created_at, sites_total, "
                       "sites_succeeded, sites_failed, raw_jobs_found, normalized_jobs, canonical_jobs_touched, "
                       "eligible_jobs) VALUES ('r1', '2026-09-01', '2026-09-01', 'success', '2026-09-01', "
                       "0, 0, 0, 0, 0, 0, 0)"))
        c.execute(text("INSERT INTO jobs (title, description, requirements, first_seen_at, created_at, updated_at, "
                       "status, content_hash) VALUES ('Dev', '', '', '2026-09-01', '2026-09-01', '2026-09-01', "
                       "'active', 'h')"))
        c.execute(text("INSERT INTO job_sources (job_id, recruitment_company, source_job_id, source_url, "
                       "source_url_fingerprint, external_title, first_seen_at, last_seen_at, status, "
                       "first_scrape_run_id, last_scrape_run_id) VALUES (1, 'Matrix', '17', 'u', 'fp', 'Dev  Ops!', "
                       "'2026-09-01 06:00:00', '2026-09-02 06:00:00', 'active', 'r1', 'r1')"))
    command.upgrade(alembic_cfg, "head")
    with engine.connect() as c:
        row = c.execute(text("SELECT recruitment_company, posting_key, title_key, reposts FROM posting_history")).one()
    assert tuple(row) == ("Matrix", "id:17", "dev ops", 0)
    command.downgrade(alembic_cfg, "0004")
    engine.dispose()
