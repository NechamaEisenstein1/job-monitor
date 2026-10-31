"""Shared salary offers: members share and withdraw their own, everyone signed in compares the
approved ones of a level, the admin approves each before it counts. Rules live in
domain/services/salary_offer_rules.py, the figures in domain/services/salary_offer_statistics.py."""
from __future__ import annotations

from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import datetime

from backend.application.salary_offer_dto import LevelSummaryDto, MySalaryOfferDto, SalaryOfferDto
from backend.domain.enums import ExperienceLevel, SubmissionStatus
from backend.domain.models import User
from backend.domain.salary_offers import ClientType, SalaryOffer, SalaryOfferDraft
from backend.domain.services.salary_offer_rules import SalaryOfferError, clean_salary_offer, months_before
from backend.domain.services.salary_offer_statistics import summarize_level
from backend.infrastructure.repositories.salary_offers import SqlSalaryOfferRepository


@dataclass(frozen=True)
class SalaryOfferQuery:
    level: ExperienceLevel
    months_back: int
    role_type: str | None = None
    client_type: ClientType | None = None

    def includes(self, offer: SalaryOffer) -> bool:
        return (self.role_type in (None, offer.role_type)) and (self.client_type in (None, offer.client_type))


class SalaryOfferService:
    def __init__(self, repo: SqlSalaryOfferRepository, clock: Callable[[], datetime], role_types: Collection[str]):
        self._repo = repo
        self._now = clock
        self._role_types = role_types

    # ------------------------------------------------------------------ comparing

    def approved_offers(self, query: SalaryOfferQuery) -> list[SalaryOfferDto]:
        return [SalaryOfferDto.model_validate(offer) for offer in self._matching(query)]

    def level_summary(self, query: SalaryOfferQuery) -> LevelSummaryDto:
        return LevelSummaryDto.model_validate(summarize_level(self._matching(query)))

    def _matching(self, query: SalaryOfferQuery) -> list[SalaryOffer]:
        offered_since = months_before(self._now().date(), query.months_back)
        return [o for o in self._repo.approved_for_level(query.level, offered_since) if query.includes(o)]

    # ------------------------------------------------------------------ sharing

    def share(self, user: User, draft: SalaryOfferDraft, *, received_personally: bool) -> int:
        offer = clean_salary_offer(draft, received_personally=received_personally, allowed_roles=self._role_types,
                                   today=self._now().date())
        return self._repo.add_pending(offer, user.id, self._now())

    def shared_by(self, user: User) -> list[MySalaryOfferDto]:
        return [MySalaryOfferDto.model_validate(offer) for offer in self._repo.submitted_by(user.id)]

    def withdraw(self, user: User, offer_id: int) -> None:
        if not self._repo.delete_submitted_by(offer_id, user.id):
            raise SalaryOfferError("not_found", 404)

    # ------------------------------------------------------------------ review (admin)

    def waiting_for_review(self) -> list[SalaryOfferDto]:
        return [SalaryOfferDto.model_validate(offer) for offer in self._repo.pending()]

    def review(self, offer_id: int, *, approve: bool) -> None:
        status = SubmissionStatus.APPROVED if approve else SubmissionStatus.REJECTED
        if not self._repo.set_status_of_pending(offer_id, status, self._now()):
            raise SalaryOfferError("not_found", 404)
