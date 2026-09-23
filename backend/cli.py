"""Command-line entry point.

    python -m backend.cli run [--date YYYY-MM-DD]      one full pipeline run (date defaults to today, Israel time)
    python -m backend.cli probe [--source NAME ...]    fetch live sources, print a report, write nothing
    python -m backend.cli create-user --email E --name N [--admin] [--experienced]
                                                       create an account (password is prompted)
    python -m backend.cli ensure-admins                grant admin to verified accounts in ADMIN_EMAILS
    python -m backend.cli copy-data --source URL       copy all data from URL into DATABASE_URL (must be empty)
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from datetime import date

from backend.application.services.scraper_executor import ScraperExecutor
from backend.application.use_cases.accounts import AccountError
from backend.bootstrap import account_service, http_client, local_today, pipeline_from_settings, utcnow
from backend.config.settings import Settings, load_matching_config, load_sources_config
from backend.domain.enums import ExperienceLevel, RunStatus, ScrapeStatus
from backend.infrastructure.db.session import make_engine, make_session_factory
from backend.infrastructure.repositories.users import DuplicateError
from backend.domain.services.normalization import normalize_raw_job
from backend.domain.services.validation import validate_job
from backend.infrastructure.scrapers.registry import build_scrapers, is_enabled
from backend.observability import configure_logging


async def _run(scheduled_date: date | None) -> RunStatus:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    async with pipeline_from_settings(settings) as pipeline:
        run = await pipeline.run(scheduled_date or local_today(load_matching_config(settings.config_dir)))
    return run.status


async def _probe(only: list[str]) -> bool:
    settings = Settings.from_env()
    configure_logging("WARNING")
    cfg = load_matching_config(settings.config_dir)
    sources = load_sources_config(settings.config_dir)
    wanted = {s.casefold() for s in only}
    selected = [s for s in sources if not wanted or s.name.casefold() in wanted]
    for s in selected:
        if not is_enabled(s):
            print(f"-- {s.name:12} disabled: {s.options.get('note', '')}")
    async with http_client(cfg) as http:
        scrapers = build_scrapers([s for s in selected if is_enabled(s)], http)
        results = await ScraperExecutor(cfg.scraper.max_concurrent_workers, utcnow).execute_all(scrapers)

    all_ok = True
    for r in results:
        jobs = [normalize_raw_job(j) for j in r.raw_jobs]
        invalid = sum(1 for j in jobs if validate_job(j))
        with_loc = sum(1 for j in jobs if j.location)
        with_req = sum(1 for j in jobs if j.requirements)
        seconds = (r.finished_at - r.started_at).total_seconds()
        ok = r.status == ScrapeStatus.SUCCESS
        all_ok &= ok
        print(f"{'OK' if ok else '!!'} {r.site:12} {r.status.value:13} jobs={len(jobs):4} invalid={invalid:3} "
              f"with_location={with_loc:4} with_requirements={with_req:4} {seconds:6.1f}s")
        if r.error:
            print(f"     error: {r.error}")
        for j in jobs[:2]:
            print(f"     · [{j.source_job_id}] {j.title[:60]} | {j.location or '-'} | {j.source_url[:70]}")
    return all_ok


def _create_user(email: str, name: str, admin: bool, experienced: bool) -> int:
    settings = Settings.from_env()
    password = getpass.getpass("Password (min 10 chars): ")
    if password != getpass.getpass("Repeat password: "):
        print("Passwords do not match.")
        return 1
    with make_session_factory(make_engine(settings.database_url))() as session:
        try:
            user = account_service(session, load_matching_config(settings.config_dir)).create_user(
                email, name, password, is_admin=admin,
                level=ExperienceLevel.EXPERIENCED if experienced else ExperienceLevel.JUNIOR)
        except AccountError as exc:
            print(f"Error: {exc.code}")
            return 1
        except DuplicateError:
            print("Error: email already registered")
            return 1
    print(f"Created user #{user.id} {user.email}{' (admin)' if admin else ''}")
    return 0


def _ensure_admins() -> int:
    settings = Settings.from_env()
    cfg = load_matching_config(settings.config_dir)
    if not cfg.users.admin_email_set:
        print("ADMIN_EMAILS is empty - set it in .env (comma-separated).")
        return 1
    with make_session_factory(make_engine(settings.database_url))() as session:
        promoted = account_service(session, cfg).promote_designated_admins()
    print(f"Promoted {len(promoted)} account(s)")
    for user in promoted:
        print(f"  - {user.email}")
    print("Addresses without a verified account are promoted automatically when they sign in.")
    return 0


def _copy_data(source: str) -> int:
    from backend.infrastructure.db.copy import TargetNotEmptyError, copy_database

    target = Settings.from_env().database_url
    if source.rstrip("/") == target.rstrip("/"):
        print("Source and target are the same database.")
        return 1
    print(f"Copying {source.split('@')[-1]}  ->  {target.split('@')[-1]}")  # never print credentials
    try:
        copied = copy_database(source, target)
    except TargetNotEmptyError as exc:
        print(f"Refusing to copy: {exc}")
        return 1
    for table, count in copied.items():
        print(f"  {table:22} {count:6}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="job-monitor")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="execute one scrape run")
    run.add_argument("--date", type=date.fromisoformat, default=None, help="scheduled date (default: today in Israel)")
    probe = sub.add_parser("probe", help="fetch live sources and print what they return (no DB writes)")
    probe.add_argument("--source", action="append", default=[], help="source name (repeatable); default: all")
    create = sub.add_parser("create-user", help="create an account; the password is prompted")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--admin", action="store_true")
    create.add_argument("--experienced", action="store_true", help="experienced profile (default: junior)")
    sub.add_parser("ensure-admins", help="grant admin to verified accounts listed in ADMIN_EMAILS")
    copy = sub.add_parser("copy-data", help="copy all data from --source into DATABASE_URL (target must be empty)")
    copy.add_argument("--source", required=True, help="e.g. sqlite:///job_monitor.db")
    args = parser.parse_args()

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # Hebrew output on Windows consoles

    if args.command == "run":
        status = asyncio.run(_run(args.date))
        return 1 if status == RunStatus.FAILED else 0
    if args.command == "probe":
        return 0 if asyncio.run(_probe(args.source)) else 1
    if args.command == "create-user":
        return _create_user(args.email, args.name, args.admin, args.experienced)
    if args.command == "ensure-admins":
        return _ensure_admins()
    if args.command == "copy-data":
        return _copy_data(args.source)
    return 2


if __name__ == "__main__":
    sys.exit(main())
