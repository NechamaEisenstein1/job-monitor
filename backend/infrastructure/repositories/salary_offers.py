"""Salary offer persistence."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from backend.domain.enums import ExperienceLevel, SubmissionStatus
from backend.domain.salary_offers import (
    ClientType, ContributionBase, ExtraKind, OfferOutcome, SalaryExtra, SalaryOffer, SalaryOfferDraft, SickPay,
    StudyFundStart,
)
from backend.infrastructure.db.orm import SalaryOfferRow


def _to_offer(row: SalaryOfferRow) -> SalaryOffer:
    return SalaryOffer(
        id=row.id, submitted_by=row.submitted_by, status=SubmissionStatus(row.status), created_at=row.created_at,
        level=ExperienceLevel(row.level), role_type=row.role_type, agency=row.agency,
        client_type=ClientType(row.client_type), offered_month=row.offered_month, outcome=OfferOutcome(row.outcome),
        base_salary=row.base_salary,
        extras=tuple(SalaryExtra(ExtraKind(e["kind"]), e["amount"], e["included_in_total"]) for e in row.extras),
        hours_per_day=row.hours_per_day, vacation_days=row.vacation_days, sick_pay=SickPay(row.sick_pay),
        contribution_base=ContributionBase(row.contribution_base), contribution_percent=row.contribution_percent,
        study_fund_start=StudyFundStart(row.study_fund_start), details=row.details,
    )


def _draft_columns(draft: SalaryOfferDraft) -> dict:
    return {
        "level": draft.level.value, "role_type": draft.role_type, "agency": draft.agency,
        "client_type": draft.client_type.value, "offered_month": draft.offered_month, "outcome": draft.outcome.value,
        "base_salary": draft.base_salary,
        "extras": [{"kind": e.kind.value, "amount": e.amount, "included_in_total": e.included_in_total}
                   for e in draft.extras],
        "hours_per_day": draft.hours_per_day, "vacation_days": draft.vacation_days, "sick_pay": draft.sick_pay.value,
        "contribution_base": draft.contribution_base.value, "contribution_percent": draft.contribution_percent,
        "study_fund_start": draft.study_fund_start.value, "details": dict(draft.details),
    }


class SqlSalaryOfferRepository:
    def __init__(self, session: Session):
        self._s = session

    def add_pending(self, draft: SalaryOfferDraft, submitted_by: int, now: datetime) -> int:
        row = SalaryOfferRow(**_draft_columns(draft), submitted_by=submitted_by,
                             status=SubmissionStatus.PENDING.value, created_at=now)
        self._s.add(row)
        self._s.commit()
        return row.id

    def approved_for_level(self, level: ExperienceLevel, offered_since: date) -> list[SalaryOffer]:
        """Most recent offer first."""
        return self._list(SalaryOfferRow.status == SubmissionStatus.APPROVED.value, SalaryOfferRow.level == level.value,
                          SalaryOfferRow.offered_month >= offered_since)

    def pending(self) -> list[SalaryOffer]:
        return self._list(SalaryOfferRow.status == SubmissionStatus.PENDING.value)

    def submitted_by(self, user_id: int) -> list[SalaryOffer]:
        return self._list(SalaryOfferRow.submitted_by == user_id)

    def set_status_of_pending(self, offer_id: int, status: SubmissionStatus, now: datetime) -> bool:
        changed = self._s.execute(
            update(SalaryOfferRow)
            .where(SalaryOfferRow.id == offer_id, SalaryOfferRow.status == SubmissionStatus.PENDING.value)
            .values(status=status.value, reviewed_at=now)
        ).rowcount
        self._s.commit()
        return bool(changed)

    def delete_submitted_by(self, offer_id: int, user_id: int) -> bool:
        deleted = self._s.execute(
            delete(SalaryOfferRow).where(SalaryOfferRow.id == offer_id, SalaryOfferRow.submitted_by == user_id)
        ).rowcount
        self._s.commit()
        return bool(deleted)

    def _list(self, *conditions) -> list[SalaryOffer]:  # noqa: ANN002
        query = select(SalaryOfferRow).where(*conditions).order_by(
            SalaryOfferRow.offered_month.desc(), SalaryOfferRow.id.desc())
        return [_to_offer(row) for row in self._s.scalars(query)]
