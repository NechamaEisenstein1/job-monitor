from __future__ import annotations

from datetime import datetime

import pytest
from alembic import command
from alembic.config import Config

from backend.config.settings import PROJECT_ROOT, MatchingConfig, load_matching_config
from backend.domain.enums import JobStatus
from backend.domain.models import Job
from backend.infrastructure.db.session import make_engine, make_session_factory

NOW = datetime(2026, 9, 23, 6, 0, 0)


@pytest.fixture
def cfg() -> MatchingConfig:
    return load_matching_config(PROJECT_ROOT / "config")


@pytest.fixture
def session_factory(tmp_path):
    """A fresh SQLite DB built by the real Alembic migrations."""
    url = f"sqlite:///{tmp_path / 'test.db'}"
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "backend/infrastructure/db/migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    alembic_cfg.attributes["configure_logger"] = False
    command.upgrade(alembic_cfg, "head")
    engine = make_engine(url)
    yield make_session_factory(engine)
    engine.dispose()


def make_job(**overrides) -> Job:
    values = dict(
        id=1, title="Junior Backend Developer", description="", requirements="",
        client_company="Intel", employment_type=None, location="Jerusalem", region=None,
        published_at=None, first_seen_at=NOW, created_at=NOW, updated_at=NOW, last_seen_at=NOW,
        status=JobStatus.ACTIVE, content_hash="a" * 64,
    )
    values.update(overrides)
    return Job(**values)


# ------------------------------------------------------------------ API / accounts helpers

class CapturingSender:
    """Records emails instead of sending them. Set `fail_for` to simulate SMTP errors."""

    def __init__(self):
        self.sent: list[tuple[str, object]] = []
        self.fail_for: set[str] = set()

    def send(self, recipient, email):
        if recipient in self.fail_for:
            raise ConnectionError("smtp down")
        self.sent.append((recipient, email))

    def to(self, recipient):
        return [e for r, e in self.sent if r == recipient]


PASSWORD = "correct-horse-battery"


@pytest.fixture
def world(cfg, session_factory, tmp_path):
    """Migrated DB + two users + one demo pipeline run (with per-user alerts) + an API client factory."""
    import asyncio

    from fastapi.testclient import TestClient

    from backend.application.services.notification import NotificationService
    from backend.application.services.scraper_executor import ScraperExecutor
    from backend.application.use_cases.run_pipeline import RunPipeline
    from backend.bootstrap import account_service, user_alert_service
    from backend.config.settings import Settings
    from backend.domain.enums import ExperienceLevel
    from backend.domain.services.evaluation import JobEvaluationService
    from backend.infrastructure.repositories.sql import SqlNotificationRepository, SqlUnitOfWork
    from backend.infrastructure.scrapers.generic import FixtureScraper
    from backend.main import create_app

    settings = Settings(database_url=str(session_factory.kw["bind"].url), config_dir=PROJECT_ROOT / "config",
                        email_outbox_dir=tmp_path, smtp=None, log_level="WARNING")
    sender = CapturingSender()
    with session_factory() as s:
        accounts = account_service(s, cfg)
        admin = accounts.create_user("admin@example.com", "מנהלת", PASSWORD, is_admin=True)
        junior = accounts.create_user("junior@example.com", "דנה", PASSWORD)
        senior = accounts.create_user("senior@example.com", "יוסי", PASSWORD, level=ExperienceLevel.EXPERIENCED)

    def run_day(day: str):
        with session_factory() as s, session_factory() as ns, session_factory() as als:
            scrapers = [FixtureScraper(n, PROJECT_ROOT / f"fixtures/{day}/{n.lower()}.json") for n in ("Matrix", "HMS")]
            return asyncio.run(RunPipeline(
                SqlUnitOfWork(s), scrapers, ScraperExecutor(2, lambda: NOW), cfg,
                JobEvaluationService.from_config(cfg),
                NotificationService(SqlNotificationRepository(ns), sender, cfg.email, lambda: NOW),
                lambda: NOW, user_alerts=user_alert_service(als, settings, cfg, sender),
            ).run())

    run = run_day("day1")
    app = create_app(settings)
    app.state.sender = sender

    def client(email: str | None = None) -> TestClient:
        c = TestClient(app, headers={"X-Requested-With": "fetch"})
        if email:
            assert c.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
        return c

    class World:
        pass

    w = World()
    w.run, w.run_day, w.client, w.sender, w.app = run, run_day, client, sender, app
    w.admin, w.junior, w.senior = admin, junior, senior
    return w
