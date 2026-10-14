"""HTTP endpoints only. Every route delegates to DashboardQueries."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from backend.application.dto import (
    JobChangeDto, JobDetailDto, JobListDto, JobSourceDto, RunDetailDto, ScrapeRunDto,
    ScraperRunDto, SourceHealthDto, StatsDto,
)
from backend.api.deps import CurrentUser, current_user, require_admin
from backend.application.use_cases.queries import DashboardQueries
from backend.domain.enums import JobStatus
from backend.infrastructure.repositories.read_models import SqlReadRepository

# Everything here needs a logged-in user.
router = APIRouter(prefix="/api", dependencies=[Depends(current_user)])


def get_queries(request: Request) -> Iterator[DashboardQueries]:
    with request.app.state.session_factory() as session:
        yield DashboardQueries(SqlReadRepository(session, request.app.state.cfg.signals), request.app.state.sources)


Queries = Annotated[DashboardQueries, Depends(get_queries)]
JobId = Annotated[int, Path(ge=1)]
RunId = Annotated[str, Path(pattern=r"^[0-9a-fA-F-]{36}$")]


def _found(value):  # noqa: ANN001, ANN202
    if value is None:
        raise HTTPException(status_code=404, detail="not found")
    return value


@router.get("/jobs", response_model=JobListDto)
def list_jobs(
    queries: Queries,
    request: Request,
    q: Annotated[str | None, Query(max_length=200)] = None,
    location: Annotated[str | None, Query(max_length=100)] = None,
    eligible: bool | None = None,
    status: JobStatus | None = None,
    source: Annotated[str | None, Query(max_length=200)] = None,
    role_type: Annotated[str | None, Query(max_length=100, pattern=r"^[a-z_,]*$",
                                           description="comma-separated, e.g. software,qa; 'tech' = all tech roles")] = None,
    government: bool | None = None,
    level: Annotated[Literal["a", "b", "c"] | None,
                     Query(description="experience level: a = junior, b = 2+ to 4 years, c = above 4")] = None,
    sort: Literal["relevance", "newest", "updated", "score"] = "relevance",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
) -> JobListDto:
    return queries.list_jobs(q=q, location=location, eligible=eligible, status=status.value if status else None,
                             source=source, role_types=_role_types(role_type, request),
                             government=government, level=level, level_years=_level_years(request),
                             sort=sort, page=page, page_size=page_size)


def _level_years(request: Request) -> tuple[float, float]:
    exp = request.app.state.cfg.experience
    return exp.junior_max_years, exp.level_b_max_years


def _role_types(role_type: str | None, request: Request) -> list[str] | None:
    """'tech' expands to the configured eligible (technology) role types."""
    types = [r for r in (role_type or "").split(",") if r]
    if "tech" in types:
        types = [r for r in types if r != "tech"] + list(request.app.state.cfg.roles.eligible_types)
    return types or None


@router.get("/jobs/{job_id}", response_model=JobDetailDto)
def get_job(job_id: JobId, queries: Queries) -> JobDetailDto:
    return _found(queries.get_job(job_id))


@router.get("/jobs/{job_id}/sources", response_model=list[JobSourceDto])
def get_job_sources(job_id: JobId, queries: Queries) -> list[JobSourceDto]:
    _found(queries.get_job(job_id))
    return queries.job_sources(job_id)


@router.get("/jobs/{job_id}/history", response_model=list[JobChangeDto])
def get_job_history(job_id: JobId, queries: Queries) -> list[JobChangeDto]:
    _found(queries.get_job(job_id))
    return queries.job_history(job_id)


# Run information (start, finish, duration, status, per-site results) is for admins only.
@router.get("/runs", response_model=list[ScrapeRunDto], dependencies=[Depends(require_admin)])
def list_runs(queries: Queries, limit: Annotated[int, Query(ge=1, le=500)] = 50) -> list[ScrapeRunDto]:
    return queries.list_runs(limit)


@router.get("/runs/{run_id}", response_model=RunDetailDto, dependencies=[Depends(require_admin)])
def get_run(run_id: RunId, queries: Queries) -> RunDetailDto:
    return _found(queries.get_run(run_id))


@router.get("/runs/{run_id}/scrapers", response_model=list[ScraperRunDto], dependencies=[Depends(require_admin)])
def get_run_scrapers(run_id: RunId, queries: Queries) -> list[ScraperRunDto]:
    return queries.run_scrapers(run_id)


@router.get("/sources", response_model=list[SourceHealthDto])
def list_sources(queries: Queries) -> list[SourceHealthDto]:
    return queries.sources()


@router.get("/activity", response_model=list[JobChangeDto])
def recent_activity(queries: Queries, limit: Annotated[int, Query(ge=1, le=200)] = 20) -> list[JobChangeDto]:
    return queries.recent_activity(limit)


@router.get("/stats", response_model=StatsDto)
def stats(queries: Queries, user: CurrentUser) -> StatsDto:
    result = queries.stats()
    if not user.is_admin:  # run information is for admins only
        result = result.model_copy(update={"latest_run": None, "failed_sources": []})
    return result
