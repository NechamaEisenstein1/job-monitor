"""Users' "the details of this job are correct" votes."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.infrastructure.db.orm import JobRow, JobVerificationRow


class SqlVerificationRepository:
    def __init__(self, session: Session):
        self._s = session

    def job_owner(self, job_id: int) -> tuple[bool, bool, int | None]:
        """(job exists, posted manually on the site, who posted it)."""
        row = self._s.get(JobRow, job_id)
        return (row is not None, bool(row and row.is_manual), row.posted_by if row else None)

    def add(self, user_id: int, job_id: int, now: datetime) -> None:
        """Voting twice is a no-op."""
        if self._exists(user_id, job_id):
            return
        self._s.add(JobVerificationRow(job_id=job_id, user_id=user_id, created_at=now))
        try:
            self._s.commit()
        except IntegrityError:  # voted at the same moment from another tab, or the job just left the board
            self._s.rollback()

    def remove(self, user_id: int, job_id: int) -> None:
        self._s.execute(delete(JobVerificationRow).where(
            JobVerificationRow.user_id == user_id, JobVerificationRow.job_id == job_id))
        self._s.commit()

    def _exists(self, user_id: int, job_id: int) -> bool:
        return self._s.get(JobVerificationRow, (job_id, user_id)) is not None

    def count(self, job_id: int) -> int:
        return self._s.scalar(select(func.count()).select_from(JobVerificationRow)
                              .where(JobVerificationRow.job_id == job_id)) or 0

    def job_ids(self, user_id: int) -> list[int]:
        return list(self._s.scalars(select(JobVerificationRow.job_id).where(JobVerificationRow.user_id == user_id)
                                    .order_by(JobVerificationRow.job_id)))
