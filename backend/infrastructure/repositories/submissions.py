"""Job postings submitted by users without the recruiter role, waiting for an admin."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.domain.enums import SubmissionStatus
from backend.domain.models import JobSubmission
from backend.infrastructure.db.orm import JobSubmissionRow, UserRow
from backend.infrastructure.repositories.mapping import to_domain, to_values

_ENUMS = {"status": SubmissionStatus}


class SqlSubmissionRepository:
    def __init__(self, session: Session):
        self._s = session

    def add(self, submission: JobSubmission) -> JobSubmission:
        row = JobSubmissionRow(**to_values(submission))
        self._s.add(row)
        self._s.flush()
        submission.id = row.id
        return submission

    def save(self, submission: JobSubmission) -> None:
        row = self._s.get(JobSubmissionRow, submission.id)
        for key, value in to_values(submission).items():
            setattr(row, key, value)
        self._s.flush()

    def find(self, submission_id: int) -> JobSubmission | None:
        row = self._s.get(JobSubmissionRow, submission_id)
        return to_domain(row, JobSubmission, _ENUMS) if row else None

    def count_since(self, user_id: int, since: datetime) -> int:
        return self._s.scalar(select(func.count()).select_from(JobSubmissionRow).where(
            JobSubmissionRow.submitted_by == user_id, JobSubmissionRow.created_at >= since)) or 0

    def tender_number_pending(self, tender_number: str) -> bool:
        return self._s.scalar(select(func.count()).select_from(JobSubmissionRow).where(
            JobSubmissionRow.status == SubmissionStatus.PENDING.value,
            func.lower(JobSubmissionRow.tender_number) == tender_number.lower())) > 0

    def list_by_user(self, user_id: int) -> list[JobSubmission]:
        rows = self._s.scalars(select(JobSubmissionRow).where(JobSubmissionRow.submitted_by == user_id)
                               .order_by(JobSubmissionRow.created_at.desc(), JobSubmissionRow.id.desc()))
        return [to_domain(r, JobSubmission, _ENUMS) for r in rows]

    def list_with_submitter(self, status: SubmissionStatus | None,
                            limit: int = 200) -> list[tuple[JobSubmission, str | None, str | None]]:
        """(submission, submitter name, submitter email); pending: oldest first, else newest first."""
        stmt = select(JobSubmissionRow, UserRow.display_name, UserRow.email).outerjoin(
            UserRow, UserRow.id == JobSubmissionRow.submitted_by)
        if status is not None:
            stmt = stmt.where(JobSubmissionRow.status == status.value)
        if status is SubmissionStatus.PENDING:
            stmt = stmt.order_by(JobSubmissionRow.created_at, JobSubmissionRow.id)
        else:
            stmt = stmt.order_by(JobSubmissionRow.created_at.desc(), JobSubmissionRow.id.desc())
        return [(to_domain(r, JobSubmission, _ENUMS), name, email)
                for r, name, email in self._s.execute(stmt.limit(limit))]

    def count_pending(self) -> int:
        return self._s.scalar(select(func.count()).select_from(JobSubmissionRow).where(
            JobSubmissionRow.status == SubmissionStatus.PENDING.value)) or 0
