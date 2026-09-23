"""Shared dict -> RawJob mapping used by generic scrapers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import ParseError

RAW_JOB_FIELDS = (
    "source_job_id", "source_url", "title", "description", "requirements",
    "client_company", "employment_type", "location", "region", "published_at",
)


def _get_path(data: Any, path: str) -> Any:
    for part in filter(None, path.split(".")):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


def extract_items(payload: Any, items_path: str) -> list[dict]:
    items = _get_path(payload, items_path) if items_path else payload
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise ParseError(f"expected a list of objects at '{items_path or '<root>'}'")
    return items


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def to_raw_job(item: dict, recruitment_company: str, field_map: dict[str, str] | None = None) -> RawJob:
    field_map = field_map or {f: f for f in RAW_JOB_FIELDS}
    values = {f: _get_path(item, field_map[f]) if f in field_map else None for f in RAW_JOB_FIELDS}
    source_job_id = values["source_job_id"]
    return RawJob(
        recruitment_company=recruitment_company,
        source_job_id=str(source_job_id) if source_job_id not in (None, "") else None,
        source_url=str(values["source_url"] or ""),
        title=str(values["title"] or ""),
        description=str(values["description"] or ""),
        requirements=str(values["requirements"] or ""),
        client_company=values["client_company"],
        employment_type=values["employment_type"],
        location=values["location"],
        region=values["region"],
        published_at=_parse_datetime(values["published_at"]),
        metadata={},
    )
