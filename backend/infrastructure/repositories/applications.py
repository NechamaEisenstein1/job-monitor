"""Jobs a user marked "I applied" - kept after the job leaves the board."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.application.dto import JobApplicationDto
from backend.infrastructure.db.orm import JobApplicationRow, JobRow, JobSourceRow


class SqlApplicationRepository:
    def __init__(self, session: Session):
        self._s = session

    def mark(self, user_id: int, job_id: int, now: datetime) -> bool:
        """Copy the job's details in; False if the job does not exist. Marking twice is a no-op."""
        job = self._s.get(JobRow, job_id)
        if job is None:
            return False
        if not self._exists(user_id, job_id):
            url = self._s.scalar(select(JobSourceRow.source_url).where(JobSourceRow.job_id == job_id)
                                 .order_by(JobSourceRow.id).limit(1))
            self._s.add(JobApplicationRow(user_id=user_id, job_id=job_id, title=job.title,
                                          client_company=job.client_company, location=job.location,
                                          source_url=url, applied_at=now))
            try:
                self._s.commit()
            except IntegrityError:
                self._s.rollback()
                if self._exists(user_id, job_id):  # marked at the same moment from another tab
                    return True
                if self._s.get(JobRow, job_id) is None:  # the daily refresh removed the job meanwhile
                    return False
                raise
        return True

    def _exists(self, user_id: int, job_id: int) -> bool:
        return self._s.scalar(select(JobApplicationRow.id).where(
            JobApplicationRow.user_id == user_id, JobApplicationRow.job_id == job_id)) is not None

    def unmark(self, user_id: int, job_id: int) -> None:
        self._s.execute(delete(JobApplicationRow).where(
            JobApplicationRow.user_id == user_id, JobApplicationRow.job_id == job_id))
        self._s.commit()

    def remove(self, user_id: int, application_id: int) -> bool:
        """Delete one entry by its own id (works after the job is gone, when job_id is NULL)."""
        result = self._s.execute(delete(JobApplicationRow).where(
            JobApplicationRow.user_id == user_id, JobApplicationRow.id == application_id))
        self._s.commit()
        return result.rowcount > 0

    def list(self, user_id: int) -> list[JobApplicationDto]:
        rows = self._s.scalars(select(JobApplicationRow).where(JobApplicationRow.user_id == user_id)
                               .order_by(JobApplicationRow.applied_at.desc(), JobApplicationRow.id.desc()))
        return [JobApplicationDto(id=r.id, job_id=r.job_id, title=r.title, client_company=r.client_company,
                                  location=r.location, source_url=r.source_url, applied_at=r.applied_at,
                                  job_removed=r.job_id is None) for r in rows]
