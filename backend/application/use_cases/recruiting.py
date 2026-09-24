"""Recruiter postings and the points economy: publishing earns points, points pay for
subscriptions and featured placement. Subscriptions are free (price 0) until a payment
provider exists; the checkout already routes through one pipeline for both methods."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from backend.config.settings import BillingConfig
from backend.domain.enums import JobStatus, PaymentMethod, PointAction, SubscriptionStatus
from backend.domain.models import Job, JobContentSnapshot, PointTransaction, Subscription, User
from backend.domain.services.evaluation import JobEvaluationService
from backend.infrastructure.repositories.billing import InsufficientPointsError, SqlBillingRepository
from backend.infrastructure.repositories.sql import SqlJobEvaluationRepository, SqlJobRepository


class RecruitingError(Exception):
    """User-facing failure. `code` is stable for the UI to translate."""

    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


def _clean(value: str | None, max_len: int, code: str, *, required: bool) -> str | None:
    value = " ".join((value or "").split())
    if not value:
        if required:
            raise RecruitingError(code)
        return None
    if len(value) > max_len:
        raise RecruitingError(code)
    return value


def _body(value: str | None, max_len: int, code: str) -> str:
    """Multi-line text: keep line breaks, trim each line."""
    value = "\n".join(line.strip() for line in (value or "").strip().splitlines())
    if len(value) > max_len:
        raise RecruitingError(code)
    return value


@dataclass(frozen=True)
class ManualJobInput:
    title: str
    description: str
    requirements: str = ""
    tender_number: str | None = None
    government_ministry: str | None = None
    location: str | None = None


@dataclass(frozen=True)
class PublishResult:
    job: Job
    points_awarded: int
    balance: int


class ManualJobService:
    def __init__(self, *, jobs: SqlJobRepository, evaluations: SqlJobEvaluationRepository,
                 billing: SqlBillingRepository, evaluator: JobEvaluationService, cfg: BillingConfig,
                 clock: Callable[[], datetime]):
        self._jobs = jobs
        self._evaluations = evaluations
        self._billing = billing
        self._evaluator = evaluator
        self._cfg = cfg
        self._clock = clock

    def publish(self, user: User, data: ManualJobInput) -> PublishResult:
        if not user.can_post_jobs:
            raise RecruitingError("recruiter_only", 403)
        title = _clean(data.title, 500, "invalid_title", required=True)
        description = _body(data.description, 20000, "invalid_description")
        if not description:
            raise RecruitingError("invalid_description")
        tender = _clean(data.tender_number, 100, "invalid_tender_number", required=False)
        ministry = _clean(data.government_ministry, 200, "invalid_ministry", required=False)
        if tender and self._jobs.tender_number_taken(tender):
            raise RecruitingError("duplicate_tender_number", 409)

        now = self._clock()
        snapshot = JobContentSnapshot(
            title=title, description=description, requirements=_body(data.requirements, 20000, "invalid_requirements"),
            location=_clean(data.location, 200, "invalid_location", required=False),
            employment_type=None, client_company=ministry)
        job = Job(
            id=None, title=snapshot.title, description=snapshot.description, requirements=snapshot.requirements,
            client_company=snapshot.client_company, employment_type=None, location=snapshot.location, region=None,
            published_at=now, first_seen_at=now, created_at=now, updated_at=now, last_seen_at=now,
            status=JobStatus.ACTIVE, content_hash=snapshot.content_hash,
            is_manual=True, posted_by=user.id, tender_number=tender, government_ministry=ministry)
        try:
            self._jobs.save(job)
        except IntegrityError as exc:  # lost a race on the unique tender number
            self._billing.rollback()
            raise RecruitingError("duplicate_tender_number", 409) from exc

        evaluation = self._evaluator.evaluate(job, None, now)
        if tender or ministry:
            # A ministry/tender number is an explicit statement, stronger than keyword detection.
            evaluation.is_government_tender = True
            if "government_tender" not in evaluation.matched_rules:
                evaluation.matched_rules.append("government_tender")
        self._evaluations.add(evaluation)

        awarded = 0
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if self._cfg.points_per_manual_job and \
                self._billing.awarded_posts_since(user.id, day_start) < self._cfg.max_awarded_posts_per_day:
            self._billing.apply(user.id, self._cfg.points_per_manual_job, PointAction.JOB_POSTED, now,
                                reference=f"job:{job.id}")
            awarded = self._cfg.points_per_manual_job
        self._billing.commit()
        return PublishResult(job=job, points_awarded=awarded, balance=self._billing.balance(user.id))

    def _owned(self, user: User, job_id: int) -> Job:
        job = self._jobs.find(job_id)
        if job is None or not job.is_manual:
            raise RecruitingError("not_found", 404)
        if job.posted_by != user.id and not user.is_admin:
            raise RecruitingError("not_found", 404)  # never reveal other recruiters' postings
        return job

    def remove(self, user: User, job_id: int) -> int:
        """Delete a posting and take back the points it earned, so posting and deleting
        cannot be used to farm points. A recruiter needs the points to still be there;
        an admin removing spam may leave the poster in debt. Returns the reversed amount."""
        job = self._owned(user, job_id)
        award = self._billing.award_for(f"job:{job.id}")
        reversed_amount = 0
        if award and job.posted_by is not None:
            try:
                self._billing.apply(job.posted_by, -award.amount, PointAction.JOB_REMOVED, self._clock(),
                                    reference=f"job:{job.id}", allow_negative=user.is_admin)
            except InsufficientPointsError as exc:
                self._billing.rollback()
                raise RecruitingError("points_already_spent", 409) from exc
            reversed_amount = award.amount
        self._jobs.delete_many([job.id])
        self._billing.commit()
        return reversed_amount

    def feature(self, user: User, job_id: int) -> Job:
        """Spend points to list a posting first for featured_job_days (extends if already featured)."""
        job = self._owned(user, job_id)
        now = self._clock()
        try:
            self._billing.apply(user.id, -self._cfg.featured_job_points, PointAction.FEATURED_JOB, now,
                                reference=f"job:{job.id}")
        except InsufficientPointsError as exc:
            self._billing.rollback()
            raise RecruitingError("insufficient_points", 402) from exc
        start = max(now, job.featured_until or now)
        job.featured_until = start + timedelta(days=self._cfg.featured_job_days)
        self._jobs.save(job)
        self._billing.commit()
        return job

    def list_mine(self, user: User, *, everyone: bool = False) -> list[Job]:
        return self._jobs.list_posted_by(None if everyone and user.is_admin else user.id)


@dataclass(frozen=True)
class SubscriptionState:
    status: SubscriptionStatus
    current: Subscription | None
    trial_available: bool
    price_ils: float
    price_points: int
    days: int
    trial_days: int


class BillingService:
    def __init__(self, *, billing: SqlBillingRepository, cfg: BillingConfig, clock: Callable[[], datetime]):
        self._billing = billing
        self._cfg = cfg
        self._clock = clock

    # ------------------------------------------------------------- points

    def wallet(self, user: User, limit: int = 50) -> tuple[int, list[PointTransaction]]:
        return self._billing.balance(user.id), self._billing.history(user.id, limit)

    # ------------------------------------------------------------- subscriptions

    def state(self, user: User) -> SubscriptionState:
        """Effective status from the subscription rows; the users column is kept in sync
        here (lazily), so an expired subscription reads as inactive without a cron job."""
        now = self._clock()
        current = self._billing.current_subscription(user.id, now)
        status = current.status if current else SubscriptionStatus.INACTIVE
        if self._billing.stored_status(user.id) is not status:
            self._billing.set_status(user.id, status)
            self._billing.commit()
        return SubscriptionState(
            status=status, current=current, trial_available=not self._billing.had_trial(user.id),
            price_ils=self._cfg.subscription_price_ils, price_points=self._cfg.subscription_price_points,
            days=self._cfg.subscription_days, trial_days=self._cfg.trial_days)

    def start_trial(self, user: User) -> SubscriptionState:
        if self._cfg.trial_days <= 0:
            raise RecruitingError("trial_unavailable", 409)
        if self._billing.had_trial(user.id):
            raise RecruitingError("trial_already_used", 409)
        if self._billing.current_subscription(user.id, self._clock()):
            raise RecruitingError("already_subscribed", 409)
        self._grant(user, SubscriptionStatus.TRIAL, days=self._cfg.trial_days, paid=0.0, points=0, method="trial")
        return self.state(user)

    def checkout(self, user: User, method: PaymentMethod) -> SubscriptionState:
        """One pipeline for every way to pay. FREE is accepted only while the price is 0;
        POINTS redeems subscription_price_points. A paid (ILS) price needs a payment
        provider, which does not exist yet - so it is refused rather than given away."""
        price, points = self._cfg.subscription_price_ils, 0
        if method is PaymentMethod.FREE:
            if price > 0:
                raise RecruitingError("payment_required", 402)
        elif method is PaymentMethod.POINTS:
            points, price = self._cfg.subscription_price_points, 0.0
        now = self._clock()
        if points:
            try:
                self._billing.apply(user.id, -points, PointAction.SUBSCRIPTION, now, reference="subscription")
            except InsufficientPointsError as exc:
                self._billing.rollback()
                raise RecruitingError("insufficient_points", 402) from exc
        self._grant(user, SubscriptionStatus.ACTIVE, days=self._cfg.subscription_days, paid=price, points=points,
                    method=method.value)
        return self.state(user)

    def _grant(self, user: User, status: SubscriptionStatus, *, days: int, paid: float, points: int,
               method: str) -> None:
        """New period starts when the current one ends, so renewing early never loses days."""
        now = self._clock()
        latest = self._billing.latest_expiry(user.id)
        start = latest if latest and latest > now else now
        sub = self._billing.add_subscription(Subscription(
            id=None, user_id=user.id, status=status, amount_paid=paid, points_spent=points, payment_method=method,
            starts_at=start, expires_at=start + timedelta(days=days), created_at=now))
        if sub.starts_at <= now:
            self._billing.set_status(user.id, status)
        self._billing.commit()
