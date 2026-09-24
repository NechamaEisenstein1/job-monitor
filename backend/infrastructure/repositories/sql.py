"""SQLAlchemy repositories. Persistence only."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import case, delete, func, literal, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.domain.enums import (
    JobChange, JobSourceStatus, JobStatus, RunStatus, ScrapeStatus,
)
from backend.domain.models import (
    Job, JobChangeRecord, JobEvaluation, JobSource, PostingHistory, ScrapeRun, ScraperRun, SourceIdentity,
)
from backend.infrastructure.db.orm import (
    JobChangeRow, JobEvaluationRow, JobRow, JobSourceRow, OutreachMessageRow, PostingHistoryRow, ScrapeRunRow,
    ScraperRunRow, SentNotificationRow, UserJobAlertRow,
)
from backend.infrastructure.repositories.mapping import to_domain, to_values

_JOB_ENUMS = {"status": JobStatus}
_SOURCE_ENUMS = {"status": JobSourceStatus}


def _upsert(session: Session, row_cls: type, obj) -> None:  # noqa: ANN001
    """Insert when obj.id is None, otherwise update in place; sets obj.id."""
    values = to_values(obj)
    if obj.id is None:
        row = row_cls(**values)
        session.add(row)
        session.flush()
        obj.id = row.id
    else:
        row = session.get(row_cls, obj.id)
        for key, value in values.items():
            setattr(row, key, value)
        session.flush()


class SqlJobRepository:
    def __init__(self, session: Session):
        self._s = session

    def get(self, job_id: int) -> Job:
        row = self._s.get(JobRow, job_id)
        if row is None:
            raise LookupError(f"job {job_id} not found")
        return to_domain(row, Job, _JOB_ENUMS)

    def save(self, job: Job) -> Job:
        _upsert(self._s, JobRow, job)
        return job

    def delete_many(self, job_ids: list[int]) -> None:
        """Remove jobs and everything that references them (history, evaluations,
        remaining postings, per-user alert and outreach records)."""
        if not job_ids:
            return
        for row_cls in (JobChangeRow, JobEvaluationRow, UserJobAlertRow, OutreachMessageRow, JobSourceRow):
            self._s.execute(delete(row_cls).where(row_cls.job_id.in_(job_ids)))
        self._s.execute(delete(JobRow).where(JobRow.id.in_(job_ids)))
        self._s.flush()

    def list_matchable(self) -> list[Job]:
        # Manual postings are never merged with scraped ones: a scraped source attached to
        # one would make the daily refresh delete it when that site drops the posting.
        rows = self._s.scalars(select(JobRow).where(
            JobRow.status != JobStatus.ARCHIVED.value, JobRow.is_manual.is_(False)).order_by(JobRow.id))
        return [to_domain(r, Job, _JOB_ENUMS) for r in rows]

    def find(self, job_id: int) -> Job | None:
        row = self._s.get(JobRow, job_id)
        return to_domain(row, Job, _JOB_ENUMS) if row else None

    def tender_number_taken(self, tender_number: str) -> bool:
        return self._s.scalar(select(func.count()).select_from(JobRow).where(
            func.lower(JobRow.tender_number) == tender_number.lower())) > 0

    def list_posted_by(self, user_id: int | None) -> list[Job]:
        """Manual postings, newest first; None = every recruiter's (admin view)."""
        stmt = select(JobRow).where(JobRow.is_manual.is_(True))
        if user_id is not None:
            stmt = stmt.where(JobRow.posted_by == user_id)
        return [to_domain(r, Job, _JOB_ENUMS) for r in self._s.scalars(stmt.order_by(JobRow.created_at.desc()))]


class SqlJobSourceRepository:
    def __init__(self, session: Session):
        self._s = session

    def find_by_identity(self, identity: SourceIdentity) -> JobSource | None:
        stmt = select(JobSourceRow).where(JobSourceRow.recruitment_company == identity.recruitment_company)
        if identity.uses_source_job_id:
            stmt = stmt.where(JobSourceRow.source_job_id == identity.source_job_id)
        else:
            stmt = stmt.where(JobSourceRow.source_job_id.is_(None),
                              JobSourceRow.source_url_fingerprint == identity.source_url_fingerprint)
        row = self._s.scalars(stmt).first()
        return to_domain(row, JobSource, _SOURCE_ENUMS) if row else None

    def save(self, source: JobSource) -> JobSource:
        _upsert(self._s, JobSourceRow, source)
        return source

    def list_for_job(self, job_id: int) -> list[JobSource]:
        rows = self._s.scalars(select(JobSourceRow).where(JobSourceRow.job_id == job_id).order_by(JobSourceRow.id))
        return [to_domain(r, JobSource, _SOURCE_ENUMS) for r in rows]

    def job_ids_for_company(self, recruitment_company: str) -> set[int]:
        return set(self._s.scalars(
            select(JobSourceRow.job_id).where(JobSourceRow.recruitment_company == recruitment_company)
        ))

    def count_for_company(self, recruitment_company: str) -> int:
        return self._s.scalar(select(func.count()).select_from(JobSourceRow).where(
            JobSourceRow.recruitment_company == recruitment_company,
            JobSourceRow.status != JobSourceStatus.ARCHIVED.value)) or 0

    def delete_many(self, source_ids: list[int]) -> None:
        """Remove postings plus the history entries that point at them."""
        if not source_ids:
            return
        self._s.execute(delete(JobChangeRow).where(JobChangeRow.job_source_id.in_(source_ids)))
        self._s.execute(delete(JobSourceRow).where(JobSourceRow.id.in_(source_ids)))
        self._s.flush()

    def list_unseen_in_run(self, recruitment_company: str, run_id: str) -> list[JobSource]:
        rows = self._s.scalars(
            select(JobSourceRow).where(
                JobSourceRow.recruitment_company == recruitment_company,
                JobSourceRow.last_scrape_run_id != run_id,
                JobSourceRow.status != JobSourceStatus.ARCHIVED.value,
            )
        )
        return [to_domain(r, JobSource, _SOURCE_ENUMS) for r in rows]


class SqlScrapeRunRepository:
    def __init__(self, session: Session):
        self._s = session

    def save(self, run: ScrapeRun) -> ScrapeRun:
        row = self._s.get(ScrapeRunRow, run.id)
        values = to_values(run, exclude=())
        if row is None:
            self._s.add(ScrapeRunRow(**values))
        else:
            for key, value in values.items():
                setattr(row, key, value)
        self._s.flush()
        return run

    def get(self, run_id: str) -> ScrapeRun:
        return to_domain(self._s.get(ScrapeRunRow, run_id), ScrapeRun, {"status": RunStatus})


class SqlScraperRunRepository:
    def __init__(self, session: Session):
        self._s = session

    def save(self, scraper_run: ScraperRun) -> ScraperRun:
        _upsert(self._s, ScraperRunRow, scraper_run)
        return scraper_run


class SqlJobEvaluationRepository:
    def __init__(self, session: Session):
        self._s = session

    def add(self, evaluation: JobEvaluation) -> None:
        self._s.add(JobEvaluationRow(**to_values(evaluation, exclude=())))
        self._s.flush()

    def list_for_run(self, run_id: str) -> list[JobEvaluation]:
        rows = self._s.scalars(select(JobEvaluationRow).where(JobEvaluationRow.scrape_run_id == run_id))
        return [to_domain(r, JobEvaluation) for r in rows]

    def delete_superseded(self, run_id: str) -> None:
        """Keep only the latest run's evaluation for each job evaluated in that run."""
        evaluated_now = select(JobEvaluationRow.job_id).where(JobEvaluationRow.scrape_run_id == run_id)
        self._s.execute(delete(JobEvaluationRow).where(
            JobEvaluationRow.scrape_run_id != run_id, JobEvaluationRow.job_id.in_(evaluated_now)))
        self._s.flush()

    def latest_for_job(self, job_id: int) -> JobEvaluation | None:
        row = self._s.scalars(
            select(JobEvaluationRow).where(JobEvaluationRow.job_id == job_id)
            .order_by(JobEvaluationRow.created_at.desc(), JobEvaluationRow.id.desc()).limit(1)
        ).first()
        return to_domain(row, JobEvaluation) if row else None


class SqlJobChangeRepository:
    def __init__(self, session: Session):
        self._s = session

    def add(self, change: JobChangeRecord) -> None:
        _upsert(self._s, JobChangeRow, change)

    def list_for_run(self, run_id: str) -> list[JobChangeRecord]:
        rows = self._s.scalars(
            select(JobChangeRow).where(JobChangeRow.scrape_run_id == run_id).order_by(JobChangeRow.id)
        )
        return [to_domain(r, JobChangeRecord, {"change_type": JobChange}) for r in rows]


class SqlNotificationRepository:
    """Idempotency via a unique (type, date, recipient) row.

    try_claim inserts a 'pending' row - the unique constraint makes concurrent
    senders race-safe. mark_sent flips it to 'sent'; release deletes it so a
    failed send can be retried. Each call commits on its own."""

    def __init__(self, session: Session):
        self._s = session

    def _key(self, notification_type: str, scheduled_date: date, recipient: str):  # noqa: ANN202
        return (SentNotificationRow.notification_type == notification_type,
                SentNotificationRow.scheduled_date == scheduled_date,
                SentNotificationRow.recipient == recipient)

    def try_claim(self, notification_type: str, scheduled_date: date, recipient: str,
                  run_id: str | None, now: datetime, stale_before: datetime) -> bool:
        for _ in range(2):
            try:
                self._s.add(SentNotificationRow(
                    notification_type=notification_type, scheduled_date=scheduled_date,
                    recipient=recipient, status="pending", scrape_run_id=run_id,
                    claimed_at=now, sent_at=None,
                ))
                self._s.commit()
                return True
            except IntegrityError:
                self._s.rollback()
                # Take over only a claim abandoned by a crashed sender.
                result = self._s.execute(
                    delete(SentNotificationRow).where(
                        *self._key(notification_type, scheduled_date, recipient),
                        SentNotificationRow.status == "pending",
                        SentNotificationRow.claimed_at < stale_before,
                    )
                )
                self._s.commit()
                if result.rowcount == 0:
                    return False
        return False

    def mark_sent(self, notification_type: str, scheduled_date: date, recipient: str, now: datetime) -> None:
        self._s.execute(
            update(SentNotificationRow)
            .where(*self._key(notification_type, scheduled_date, recipient))
            .values(status="sent", sent_at=now)
        )
        self._s.commit()

    def release(self, notification_type: str, scheduled_date: date, recipient: str) -> None:
        self._s.execute(
            delete(SentNotificationRow).where(
                *self._key(notification_type, scheduled_date, recipient),
                SentNotificationRow.status == "pending",
            )
        )
        self._s.commit()


def source_posting_key():  # noqa: ANN201
    """SQL twin of signals.posting_key() over job_sources columns."""
    return case((JobSourceRow.source_job_id.is_not(None), literal("id:") + JobSourceRow.source_job_id),
                else_=literal("url:") + JobSourceRow.source_url_fingerprint)


class SqlPostingHistoryRepository:
    def __init__(self, session: Session):
        self._s = session

    def find(self, company: str, key: str) -> PostingHistory | None:
        row = self._s.scalars(select(PostingHistoryRow).where(
            PostingHistoryRow.recruitment_company == company, PostingHistoryRow.posting_key == key)).first()
        return to_domain(row, PostingHistory) if row else None

    def find_gone_by_title(self, company: str, title_key: str) -> PostingHistory | None:
        """The most recently removed posting of this agency with the same title."""
        if not title_key:
            return None
        row = self._s.scalars(select(PostingHistoryRow).where(
            PostingHistoryRow.recruitment_company == company, PostingHistoryRow.title_key == title_key,
            PostingHistoryRow.gone_at.is_not(None)).order_by(PostingHistoryRow.gone_at.desc()).limit(1)).first()
        return to_domain(row, PostingHistory) if row else None

    def save(self, history: PostingHistory) -> PostingHistory:
        _upsert(self._s, PostingHistoryRow, history)
        return history

    def delete(self, history_id: int) -> None:
        self._s.execute(delete(PostingHistoryRow).where(PostingHistoryRow.id == history_id))

    def mark_gone(self, company: str, keys: list[str], now: datetime) -> None:
        if keys:
            self._s.execute(update(PostingHistoryRow).where(
                PostingHistoryRow.recruitment_company == company, PostingHistoryRow.posting_key.in_(keys),
            ).values(gone_at=now).execution_options(synchronize_session=False))

    def for_jobs(self, job_ids: list[int]) -> dict[int, list[PostingHistory]]:
        """History rows of each job's current postings."""
        if not job_ids:
            return {}
        rows = self._s.execute(
            select(JobSourceRow.job_id, PostingHistoryRow)
            .join(PostingHistoryRow, (PostingHistoryRow.recruitment_company == JobSourceRow.recruitment_company)
                  & (PostingHistoryRow.posting_key == source_posting_key()))
            .where(JobSourceRow.job_id.in_(job_ids)))
        result: dict[int, list[PostingHistory]] = {}
        for job_id, row in rows:
            result.setdefault(job_id, []).append(to_domain(row, PostingHistory))
        return result


class SqlUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.jobs = SqlJobRepository(session)
        self.sources = SqlJobSourceRepository(session)
        self.runs = SqlScrapeRunRepository(session)
        self.scraper_runs = SqlScraperRunRepository(session)
        self.evaluations = SqlJobEvaluationRepository(session)
        self.changes = SqlJobChangeRepository(session)
        self.history = SqlPostingHistoryRepository(session)

    def commit(self) -> None:
        self.session.commit()
