"""Recruiter postings (recruiters and admins) and the points/subscription wallet (any user)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field

from backend.api.deps import CurrentUser, DbSession, RecruiterUser, csrf_protect
from backend.application.dto import (
    BillingPricesDto, ManualJobDto, PointTransactionDto, PublishResultDto, SubscriptionDto, SubscriptionStateDto,
    WalletDto,
)
from backend.application.use_cases.recruiting import ManualJobInput, RecruitingError, SubscriptionState
from backend.bootstrap import billing_service, manual_job_service
from backend.domain.enums import PaymentMethod
from backend.domain.models import Job

router = APIRouter(prefix="/api", dependencies=[Depends(csrf_protect)])


def _fail(exc: RecruitingError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.code)


def _job_dto(job: Job) -> ManualJobDto:
    return ManualJobDto(id=job.id, title=job.title, tender_number=job.tender_number,
                        government_ministry=job.government_ministry, location=job.location,
                        status=job.status.value, created_at=job.created_at, featured_until=job.featured_until,
                        posted_by=job.posted_by)


def _state_dto(state: SubscriptionState, balance: int) -> SubscriptionStateDto:
    current = SubscriptionDto(id=state.current.id, status=state.current.status.value,
                              amount_paid=state.current.amount_paid, points_spent=state.current.points_spent,
                              payment_method=state.current.payment_method, starts_at=state.current.starts_at,
                              expires_at=state.current.expires_at) if state.current else None
    return SubscriptionStateDto(
        status=state.status.value, current=current, trial_available=state.trial_available,
        price_ils=state.price_ils, price_points=state.price_points, days=state.days, trial_days=state.trial_days,
        free_checkout=state.price_ils == 0, points_balance=balance)


# ------------------------------------------------------------------ recruiter postings

class ManualJobIn(BaseModel):
    title: str = Field(max_length=500)
    description: str = Field(max_length=20000)
    requirements: str = Field(default="", max_length=20000)
    tender_number: str | None = Field(default=None, max_length=100)
    government_ministry: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)


@router.get("/recruiter/jobs", response_model=list[ManualJobDto])
def my_postings(user: RecruiterUser, request: Request, session: DbSession, all: bool = False) -> list[ManualJobDto]:
    """The caller's own postings; an admin may pass ?all=true to see every recruiter's."""
    service = manual_job_service(session, request.app.state.cfg)
    return [_job_dto(j) for j in service.list_mine(user, everyone=all)]


@router.post("/recruiter/jobs", response_model=PublishResultDto, status_code=201)
def publish(body: ManualJobIn, user: RecruiterUser, request: Request, session: DbSession) -> PublishResultDto:
    try:
        result = manual_job_service(session, request.app.state.cfg).publish(user, ManualJobInput(**body.model_dump()))
    except RecruitingError as exc:
        raise _fail(exc) from exc
    return PublishResultDto(job=_job_dto(result.job), points_awarded=result.points_awarded, balance=result.balance)


@router.delete("/recruiter/jobs/{job_id}")
def remove(job_id: Annotated[int, Path(ge=1)], user: RecruiterUser, request: Request,
           session: DbSession) -> dict[str, int]:
    try:
        reversed_points = manual_job_service(session, request.app.state.cfg).remove(user, job_id)
    except RecruitingError as exc:
        raise _fail(exc) from exc
    return {"points_reversed": reversed_points}


@router.post("/recruiter/jobs/{job_id}/feature", response_model=ManualJobDto)
def feature(job_id: Annotated[int, Path(ge=1)], user: RecruiterUser, request: Request,
            session: DbSession) -> ManualJobDto:
    try:
        return _job_dto(manual_job_service(session, request.app.state.cfg).feature(user, job_id))
    except RecruitingError as exc:
        raise _fail(exc) from exc


# ------------------------------------------------------------------ wallet & subscription

@router.get("/billing/prices", response_model=BillingPricesDto)
def prices(_: CurrentUser, request: Request) -> BillingPricesDto:
    cfg = request.app.state.cfg.billing
    return BillingPricesDto(points_per_manual_job=cfg.points_per_manual_job,
                            max_awarded_posts_per_day=cfg.max_awarded_posts_per_day,
                            featured_job_points=cfg.featured_job_points, featured_job_days=cfg.featured_job_days)


@router.get("/billing/wallet", response_model=WalletDto)
def wallet(user: CurrentUser, request: Request, session: DbSession) -> WalletDto:
    balance, transactions = billing_service(session, request.app.state.cfg).wallet(user)
    return WalletDto(balance=balance, transactions=[
        PointTransactionDto(id=t.id, amount=t.amount, action_type=t.action_type.value, reference=t.reference,
                            created_at=t.created_at) for t in transactions])


@router.get("/billing/subscription", response_model=SubscriptionStateDto)
def subscription(user: CurrentUser, request: Request, session: DbSession) -> SubscriptionStateDto:
    service = billing_service(session, request.app.state.cfg)
    return _state_dto(service.state(user), service.wallet(user, limit=0)[0])


@router.post("/billing/subscription/trial", response_model=SubscriptionStateDto)
def start_trial(user: CurrentUser, request: Request, session: DbSession) -> SubscriptionStateDto:
    service = billing_service(session, request.app.state.cfg)
    try:
        state = service.start_trial(user)
    except RecruitingError as exc:
        raise _fail(exc) from exc
    return _state_dto(state, service.wallet(user, limit=0)[0])


class CheckoutIn(BaseModel):
    method: PaymentMethod


@router.post("/billing/subscription/checkout", response_model=SubscriptionStateDto)
def checkout(body: CheckoutIn, user: CurrentUser, request: Request, session: DbSession) -> SubscriptionStateDto:
    service = billing_service(session, request.app.state.cfg)
    try:
        state = service.checkout(user, body.method)
    except RecruitingError as exc:
        raise _fail(exc) from exc
    return _state_dto(state, service.wallet(user, limit=0)[0])
