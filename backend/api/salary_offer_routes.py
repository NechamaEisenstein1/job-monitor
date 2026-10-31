"""Shared salary offers: signed-in members share and compare them; the admin approves each one."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from backend.api.deps import AdminUser, CurrentUser, DbSession, csrf_protect
from backend.application.salary_offer_dto import (
    LevelSummaryDto, MySalaryOfferDto, SalaryOfferDto, SalaryOfferOptionsDto,
)
from backend.application.use_cases.salary_offers import SalaryOfferQuery, SalaryOfferService
from backend.bootstrap import salary_offer_service
from backend.domain.enums import ExperienceLevel
from backend.domain.salary_offers import (
    ClientType, ContributionBase, DetailValue, ExtraKind, OfferOutcome, SalaryExtra, SalaryOfferDraft, SickPay,
    StudyFundStart,
)
from backend.domain.services.salary_offer_rules import AGENCY_MAX, EXTRAS_MAX, SalaryOfferError
from backend.observability import log_event

router = APIRouter(prefix="/api", dependencies=[Depends(csrf_protect)])

OfferId = Annotated[int, Path(ge=1)]


def _service(request: Request, session: DbSession) -> SalaryOfferService:
    return salary_offer_service(session, request.app.state.cfg)


SalaryOffers = Annotated[SalaryOfferService, Depends(_service)]


def _query(level: ExperienceLevel, months_back: Annotated[int, Query(ge=1, le=60)] = 12,
           role_type: str | None = None, client_type: ClientType | None = None) -> SalaryOfferQuery:
    return SalaryOfferQuery(level, months_back, role_type, client_type)


OfferQuery = Annotated[SalaryOfferQuery, Depends(_query)]


def _fail(exc: SalaryOfferError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.code)


class SalaryExtraIn(BaseModel):
    kind: ExtraKind
    amount: int
    included_in_total: bool


class SalaryOfferIn(BaseModel):
    """Ranges are checked in domain/services/salary_offer_rules.py."""
    level: ExperienceLevel
    role_type: str = Field(max_length=32)
    agency: str = Field(max_length=AGENCY_MAX + 40)
    client_type: ClientType
    offered_month: date
    outcome: OfferOutcome
    base_salary: int
    extras: list[SalaryExtraIn] = Field(default_factory=list, max_length=EXTRAS_MAX)
    hours_per_day: float
    vacation_days: int
    sick_pay: SickPay
    contribution_base: ContributionBase
    contribution_percent: int
    study_fund_start: StudyFundStart
    details: dict[str, DetailValue] = Field(default_factory=dict, max_length=40)
    received_personally: bool

    def to_draft(self) -> SalaryOfferDraft:
        fields = self.model_dump(exclude={"extras", "received_personally"})
        extras = tuple(SalaryExtra(e.kind, e.amount, e.included_in_total) for e in self.extras)
        return SalaryOfferDraft(**fields, extras=extras)


@router.get("/salary-offers/options", response_model=SalaryOfferOptionsDto)
def sharing_options(request: Request, user: CurrentUser) -> SalaryOfferOptionsDto:
    return SalaryOfferOptionsDto(role_types=request.app.state.cfg.roles.eligible_types,
                                 agencies=sorted(source.name for source in request.app.state.sources))


@router.get("/salary-offers", response_model=list[SalaryOfferDto])
def approved_offers(query: OfferQuery, user: CurrentUser, offers: SalaryOffers) -> list[SalaryOfferDto]:
    return offers.approved_offers(query)


@router.get("/salary-offers/summary", response_model=LevelSummaryDto)
def level_summary(query: OfferQuery, user: CurrentUser, offers: SalaryOffers) -> LevelSummaryDto:
    return offers.level_summary(query)


@router.post("/salary-offers", status_code=201)
def share_offer(body: SalaryOfferIn, user: CurrentUser, offers: SalaryOffers) -> dict[str, int]:
    try:
        offer_id = offers.share(user, body.to_draft(), received_personally=body.received_personally)
    except SalaryOfferError as exc:
        raise _fail(exc) from exc
    log_event("salary_offer_shared", offer_id=offer_id)
    return {"id": offer_id}


@router.get("/salary-offers/mine", response_model=list[MySalaryOfferDto])
def my_offers(user: CurrentUser, offers: SalaryOffers) -> list[MySalaryOfferDto]:
    return offers.shared_by(user)


@router.delete("/salary-offers/{offer_id}", status_code=204)
def withdraw_offer(offer_id: OfferId, user: CurrentUser, offers: SalaryOffers) -> None:
    try:
        offers.withdraw(user, offer_id)
    except SalaryOfferError as exc:
        raise _fail(exc) from exc


@router.get("/admin/salary-offers", response_model=list[SalaryOfferDto])
def offers_waiting_for_review(admin: AdminUser, offers: SalaryOffers) -> list[SalaryOfferDto]:
    return offers.waiting_for_review()


@router.post("/admin/salary-offers/{offer_id}/approve", status_code=204)
def approve_offer(offer_id: OfferId, admin: AdminUser, offers: SalaryOffers) -> None:
    _review(offers, offer_id, approve=True)


@router.post("/admin/salary-offers/{offer_id}/reject", status_code=204)
def reject_offer(offer_id: OfferId, admin: AdminUser, offers: SalaryOffers) -> None:
    _review(offers, offer_id, approve=False)


def _review(offers: SalaryOfferService, offer_id: int, *, approve: bool) -> None:
    try:
        offers.review(offer_id, approve=approve)
    except SalaryOfferError as exc:
        raise _fail(exc) from exc
    log_event("salary_offer_reviewed", offer_id=offer_id, approved=approve)
