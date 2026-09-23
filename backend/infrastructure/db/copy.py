"""One-off data move between databases (e.g. the local SQLite file -> production Postgres)."""
from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import Integer, create_engine, func, select, text

from backend.config.settings import PROJECT_ROOT, normalize_database_url
from backend.infrastructure.db.orm import Base
from backend.infrastructure.db.session import make_engine

BATCH = 1000


class TargetNotEmptyError(RuntimeError):
    pass


def migrate(database_url: str) -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "backend/infrastructure/db/migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


def copy_database(source_url: str, target_url: str) -> dict[str, int]:
    """Copy every application table. The target is migrated first and must be empty,
    so an accidental second run can never duplicate or overwrite production data."""
    source_url, target_url = normalize_database_url(source_url), normalize_database_url(target_url)
    migrate(target_url)
    source, target = create_engine(source_url), make_engine(target_url)
    tables = Base.metadata.sorted_tables  # parents before children (foreign keys)

    with target.connect() as conn:
        filled = [t.name for t in tables if conn.execute(select(func.count()).select_from(t)).scalar()]
    if filled:
        raise TargetNotEmptyError(f"target already has data in: {', '.join(filled)}")

    copied: dict[str, int] = {}
    with source.connect() as src, target.begin() as dst:
        for table in tables:
            rows = [dict(r._mapping) for r in src.execute(select(table))]
            for start in range(0, len(rows), BATCH):
                dst.execute(table.insert(), rows[start:start + BATCH])
            copied[table.name] = len(rows)
        if target.dialect.name == "postgresql":
            # Rows were inserted with explicit ids: move each id sequence past the max.
            for table in tables:
                pk = list(table.primary_key.columns)
                if len(pk) == 1 and isinstance(pk[0].type, Integer) and copied[table.name]:
                    dst.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', '{pk[0].name}'), "
                        f"(SELECT MAX({pk[0].name}) FROM {table.name}))"))
    source.dispose()
    target.dispose()
    return copied
