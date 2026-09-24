"""SQLAlchemy repositories. Persistence only."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import case, delete, func, insert, literal, select, update
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


def _pin(session: Session, rows) -> None:  # noqa: ANN001
    """Keep rows alive for the session. The identity map holds rows only weakly, so a row
    already turned into a domain object is garbage-collected and the next get() goes back
    to the database - over a network (production), that is most of a run's time."""
    session.info.setdefault("pinned_rows", set()).update(rows)


def _upsert(session: Session, row_cls: type, obj):  # noqa: ANN001, ANN202
    """Insert when obj.id is None, otherwise update in place; sets obj.id; returns the row.
    Only inserts flush at once (the id is needed); updates are sent in one batch at the
    next flush/commit instead of one round trip each."""
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
    _pin(session, (row,))
    return row


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
        rows = list(self._s.scalars(select(JobRow).where(
            JobRow.status != JobStatus.ARCHIVED.value, JobRow.is_manual.is_(False)).order_by(JobRow.id)))
        _pin(self._s, rows)  # the run reads and updates these jobs again: no second trip
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


def _source_key(source_job_id: str | None, fingerprint: str) -> tuple[str, str]:
    # Same identity rule as SourceIdentity: the site's id, else the URL fingerprint.
    return ("id", source_job_id) if source_job_id is not None else ("url", fingerprint)


class SqlJobSourceRepository:
    """An agency's postings are loaded once per session (first lookup for that agency) and
    looked up in memory afterwards: one query per site instead of one per posting."""

    def __init__(self, session: Session):
        self._s = session
        self._index: dict[str, dict[tuple[str, str], JobSourceRow]] = session.info.setdefault("source_index", {})

    def _company(self, company: str) -> dict[tuple[str, str], JobSourceRow]:
        if company not in self._index:
            rows = list(self._s.scalars(select(JobSourceRow).where(JobSourceRow.recruitment_company == company)))
            _pin(self._s, rows)
            self._index[company] = {_source_key(r.source_job_id, r.source_url_fingerprint): r for r in rows}
        return self._index[company]

    def find_by_identity(self, identity: SourceIdentity) -> JobSource | None:
        key = _source_key(identity.source_job_id if identity.uses_source_job_id else None,
                          identity.source_url_fingerprint)
        row = self._company(identity.recruitment_company).get(key)
        return to_domain(row, JobSource, _SOURCE_ENUMS) if row else None

    def save(self, source: JobSource) -> JobSource:
        row = _upsert(self._s, JobSourceRow, source)
        if source.recruitment_company in self._index:
            self._index[source.recruitment_company][_source_key(row.source_job_id, row.source_url_fingerprint)] = row
        return source

    def list_for_job(self, job_id: int) -> list[JobSource]:
        rows = self._s.scalars(select(JobSourceRow).where(JobSourceRow.job_id == job_id).order_by(JobSourceRow.id))
        return [to_domain(r, JobSource, _SOURCE_ENUMS) for r in rows]

    def list_for_jobs(self, job_ids: list[int]) -> dict[int, list[JobSource]]:
        """list_for_job for many jobs in a few queries."""
        result: dict[int, list[JobSource]] = {job_id: [] for job_id in job_ids}
        ids = list(result)
        for start in range(0, len(ids), 500):
            rows = self._s.scalars(select(JobSourceRow).where(JobSourceRow.job_id.in_(ids[start:start + 500]))
                                   .order_by(JobSourceRow.id))
            for row in rows:
                result[row.job_id].append(to_domain(row, JobSource, _SOURCE_ENUMS))
        return result

    def job_ids_for_company(self, recruitment_company: str) -> set[int]:
        return {row.job_id for row in self._company(recruitment_company).values()}

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
        removed = set(source_ids)
        for rows in self._index.values():
            for key in [k for k, r in rows.items() if r.id in removed]:
                del rows[key]

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

    def add_many(self, evaluations: list[JobEvaluation]) -> None:
        """A run's evaluations in one batched INSERT (the ORM would send them one by one
        to read back each id, which nothing needs)."""
        if evaluations:
            self._s.execute(insert(JobEvaluationRow), [to_values(e, exclude=()) for e in evaluations])

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
    """Like the postings, an agency's history is loaded once per session and kept in memory."""

    def __init__(self, session: Session):
        self._s = session
        self._index: dict[str, dict[str, PostingHistoryRow]] = session.info.setdefault("history_index", {})

    def _company(self, company: str) -> dict[str, PostingHistoryRow]:
        if company not in self._index:
            rows = list(self._s.scalars(select(PostingHistoryRow).where(
                PostingHistoryRow.recruitment_company == company)))
            _pin(self._s, rows)
            self._index[company] = {r.posting_key: r for r in rows}
        return self._index[company]

    def find(self, company: str, key: str) -> PostingHistory | None:
        row = self._company(company).get(key)
        return to_domain(row, PostingHistory) if row else None

    def find_gone_by_title(self, company: str, title_key: str) -> PostingHistory | None:
        """The most recently removed posting of this agency with the same title."""
        if not title_key:
            return None
        gone = [r for r in self._company(company).values() if r.title_key == title_key and r.gone_at is not None]
        row = max(gone, key=lambda r: r.gone_at, default=None)
        return to_domain(row, PostingHistory) if row else None

    def save(self, history: PostingHistory) -> PostingHistory:
        row = _upsert(self._s, PostingHistoryRow, history)
        self._company(history.recruitment_company)[row.posting_key] = row
        return history

    def delete(self, history_id: int) -> None:
        for rows in self._index.values():
            for key, row in list(rows.items()):
                if row.id == history_id:
                    del rows[key]
                    self._s.delete(row)
                    return
        self._s.execute(delete(PostingHistoryRow).where(PostingHistoryRow.id == history_id))

    def mark_gone(self, company: str, keys: list[str], now: datetime) -> None:
        rows = self._company(company)
        for key in keys:
            if key in rows:
                rows[key].gone_at = now

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
