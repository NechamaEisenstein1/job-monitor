"""SQL read models for the dashboard. Returns DTOs; no business decisions."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from backend.application.dto import (
    EvaluationDto, JobChangeDto, JobDetailDto, JobListDto, JobListItemDto, JobSourceDto,
    ScrapeRunDto, ScraperRunDto,
)
from backend.domain.enums import JobSourceStatus, JobStatus, ScrapeStatus
from backend.infrastructure.db.orm import (
    JobChangeRow, JobEvaluationRow, JobRow, JobSourceRow, ScrapeRunRow, ScraperRunRow,
)


def _duration(start: datetime | None, end: datetime | None) -> float | None:
    return round((end - start).total_seconds(), 1) if start and end else None


def _latest_evaluation_id():  # noqa: ANN202
    return (
        select(JobEvaluationRow.id)
        .where(JobEvaluationRow.job_id == JobRow.id)
        .order_by(JobEvaluationRow.created_at.desc(), JobEvaluationRow.id.desc())
        .limit(1)
        .correlate(JobRow)
        .scalar_subquery()
    )


def run_to_dto(row: ScrapeRunRow) -> ScrapeRunDto:
    return ScrapeRunDto(
        **{c: getattr(row, c) for c in ScrapeRunDto.model_fields if hasattr(row, c)},
        duration_seconds=_duration(row.started_at, row.finished_at),
        success_ratio=round(row.sites_succeeded / row.sites_total, 3) if row.sites_total else None,
    )


class SqlReadRepository:
    def __init__(self, session: Session):
        self._s = session

    # -------------------------------------------------------------- jobs

    def list_jobs(self, *, q: str | None = None, location: str | None = None, eligible: bool | None = None,
                  status: str | None = None, source: str | None = None, role_types: list[str] | None = None,
                  government: bool | None = None, junior: bool | None = None, location_matched: bool | None = None,
                  sort: str = "relevance", page: int = 1, page_size: int = 25) -> JobListDto:
        latest_eval = _latest_evaluation_id()
        stmt = select(JobRow, JobEvaluationRow).outerjoin(JobEvaluationRow, JobEvaluationRow.id == latest_eval)
        if role_types:
            stmt = stmt.where(JobEvaluationRow.role_type.in_(role_types))
        if government is not None:
            stmt = stmt.where(JobEvaluationRow.is_government_tender.is_(government))
        if junior is not None:
            stmt = stmt.where(JobEvaluationRow.is_junior.is_(junior))
        if location_matched is not None:
            stmt = stmt.where(JobEvaluationRow.location_matched.is_(location_matched))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(JobRow.title.ilike(like), JobRow.client_company.ilike(like),
                                  JobRow.description.ilike(like)))
        if location:
            stmt = stmt.where(or_(JobRow.location.ilike(f"%{location}%"), JobRow.region.ilike(f"%{location}%")))
        if eligible is not None:
            stmt = stmt.where(JobEvaluationRow.is_eligible.is_(eligible))
        if status:
            stmt = stmt.where(JobRow.status == status)
        if source:
            stmt = stmt.where(exists().where(and_(JobSourceRow.job_id == JobRow.id,
                                                   JobSourceRow.recruitment_company == source)))

        total = self._s.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        order = {
            # rank_score is computed by the domain (junior first, then role priority, then score).
            "relevance": [JobEvaluationRow.rank_score.desc().nulls_last(), JobRow.first_seen_at.desc()],
            "newest": [JobRow.first_seen_at.desc()],
            "updated": [JobRow.updated_at.desc()],
            "score": [JobEvaluationRow.junior_score.desc().nulls_last()],
        }.get(sort, [JobEvaluationRow.rank_score.desc().nulls_last()])
        rows = self._s.execute(stmt.order_by(*order, JobRow.id.desc())
                               .offset((page - 1) * page_size).limit(page_size)).all()

        companies = self._companies_by_job([r[0].id for r in rows])
        items = [
            JobListItemDto(
                id=job.id, title=job.title, client_company=job.client_company, location=job.location,
                status=job.status,
                junior_score=ev.junior_score if ev else None, is_eligible=ev.is_eligible if ev else None,
                is_junior=ev.is_junior if ev else None, role_type=ev.role_type if ev else None,
                is_government_tender=bool(ev and ev.is_government_tender),
                source_count=len(companies.get(job.id, [])), recruitment_companies=companies.get(job.id, []),
                last_seen_at=job.last_seen_at, updated_at=job.updated_at, first_seen_at=job.first_seen_at,
            )
            for job, ev in rows
        ]
        return JobListDto(items=items, total=total, page=page, page_size=page_size)

    def count_by_role(self) -> list[tuple[str, int]]:
        latest_eval = _latest_evaluation_id()
        rows = self._s.execute(
            select(JobEvaluationRow.role_type, func.count())
            .select_from(JobRow).join(JobEvaluationRow, JobEvaluationRow.id == latest_eval)
            .where(JobRow.status == JobStatus.ACTIVE.value).group_by(JobEvaluationRow.role_type)
            .order_by(func.count().desc()))
        return [(r or "other", n) for r, n in rows]

    def count_active_by_source(self) -> list[tuple[str, int]]:
        rows = self._s.execute(
            select(JobSourceRow.recruitment_company, func.count())
            .where(JobSourceRow.status == JobSourceStatus.ACTIVE.value)
            .group_by(JobSourceRow.recruitment_company).order_by(func.count().desc()))
        return list(rows)

    def count_active_tenders(self) -> int:
        latest_eval = _latest_evaluation_id()
        return self._s.scalar(
            select(func.count()).select_from(JobRow).join(JobEvaluationRow, JobEvaluationRow.id == latest_eval)
            .where(JobRow.status == JobStatus.ACTIVE.value, JobEvaluationRow.is_government_tender.is_(True))
        ) or 0

    def _companies_by_job(self, job_ids: list[int]) -> dict[int, list[str]]:
        if not job_ids:
            return {}
        result: dict[int, list[str]] = {}
        for job_id, company in self._s.execute(
            select(JobSourceRow.job_id, JobSourceRow.recruitment_company)
            .where(JobSourceRow.job_id.in_(job_ids)).order_by(JobSourceRow.id)
        ):
            result.setdefault(job_id, []).append(company)
        return result

    def get_job(self, job_id: int) -> JobDetailDto | None:
        job = self._s.get(JobRow, job_id)
        if job is None:
            return None
        evaluation = self._s.scalars(
            select(JobEvaluationRow).where(JobEvaluationRow.job_id == job_id)
            .order_by(JobEvaluationRow.created_at.desc(), JobEvaluationRow.id.desc()).limit(1)
        ).first()
        return JobDetailDto(
            **{c: getattr(job, c) for c in JobDetailDto.model_fields if c != "evaluation"},
            evaluation=EvaluationDto.model_validate(evaluation) if evaluation else None,
        )

    def job_sources(self, job_id: int) -> list[JobSourceDto]:
        rows = self._s.scalars(select(JobSourceRow).where(JobSourceRow.job_id == job_id).order_by(JobSourceRow.id))
        return [JobSourceDto.model_validate(r) for r in rows]

    def changes(self, *, job_id: int | None = None, limit: int = 50) -> list[JobChangeDto]:
        stmt = (
            select(JobChangeRow, JobRow.title, JobSourceRow.recruitment_company)
            .join(JobRow, JobRow.id == JobChangeRow.job_id)
            .join(JobSourceRow, JobSourceRow.id == JobChangeRow.job_source_id)
            .order_by(JobChangeRow.created_at.desc(), JobChangeRow.id.desc())
            .limit(limit)
        )
        if job_id is not None:
            stmt = stmt.where(JobChangeRow.job_id == job_id)
        return [
            JobChangeDto(id=c.id, job_id=c.job_id, job_title=title, change_type=c.change_type,
                         recruitment_company=company, scrape_run_id=c.scrape_run_id, created_at=c.created_at)
            for c, title, company in self._s.execute(stmt)
        ]

    # -------------------------------------------------------------- runs

    def list_runs(self, limit: int) -> list[ScrapeRunDto]:
        rows = self._s.scalars(select(ScrapeRunRow).order_by(ScrapeRunRow.started_at.desc()).limit(limit))
        return [run_to_dto(r) for r in rows]

    def get_run(self, run_id: str) -> ScrapeRunDto | None:
        row = self._s.get(ScrapeRunRow, run_id)
        return run_to_dto(row) if row else None

    def run_scrapers(self, run_id: str) -> list[ScraperRunDto]:
        rows = self._s.scalars(select(ScraperRunRow).where(ScraperRunRow.run_id == run_id).order_by(ScraperRunRow.id))
        return [
            ScraperRunDto(**{c: getattr(r, c) for c in ScraperRunDto.model_fields if c != "duration_seconds"},
                          duration_seconds=_duration(r.started_at, r.finished_at))
            for r in rows
        ]

    def latest_scraper_run(self, site: str, successful_only: bool = False) -> ScraperRunRow | None:
        stmt = select(ScraperRunRow).where(ScraperRunRow.site == site)
        if successful_only:
            stmt = stmt.where(ScraperRunRow.status == ScrapeStatus.SUCCESS.value)
        return self._s.scalars(stmt.order_by(ScraperRunRow.started_at.desc(), ScraperRunRow.id.desc()).limit(1)).first()

    def active_source_count(self, recruitment_company: str) -> int:
        return self._s.scalar(select(func.count()).select_from(JobSourceRow).where(
            JobSourceRow.recruitment_company == recruitment_company,
            JobSourceRow.status == JobSourceStatus.ACTIVE.value)) or 0

    # -------------------------------------------------------------- stats

    def count_jobs(self, status: JobStatus) -> int:
        return self._s.scalar(select(func.count()).select_from(JobRow).where(JobRow.status == status.value)) or 0

    def count_changes(self, run_id: str, change_types: list[str]) -> int:
        return self._s.scalar(
            select(func.count(func.distinct(JobChangeRow.job_id))).where(
                JobChangeRow.scrape_run_id == run_id, JobChangeRow.change_type.in_(change_types))
        ) or 0

    def count_eligible_active_jobs(self) -> int:
        latest_eval = _latest_evaluation_id()
        return self._s.scalar(
            select(func.count()).select_from(JobRow)
            .join(JobEvaluationRow, JobEvaluationRow.id == latest_eval)
            .where(JobRow.status == JobStatus.ACTIVE.value, JobEvaluationRow.is_eligible.is_(True))
        ) or 0

    def latest_run_row(self) -> ScrapeRunRow | None:
        return self._s.scalars(select(ScrapeRunRow).order_by(ScrapeRunRow.started_at.desc()).limit(1)).first()
