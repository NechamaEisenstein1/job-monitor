"""'Send assistance request to recruiters': one personalised email per saved recruiter.

Safeguards: only the user's own recruiters; each (user, job, recruiter) is sent at most
once; a daily cap per user; replies go to the user via Reply-To."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from backend.application.use_cases.accounts import AccountError
from backend.domain.enums import OutreachStatus
from backend.domain.models import User
from backend.infrastructure.email.renderer import render_outreach
from backend.infrastructure.email.senders import EmailSender
from backend.infrastructure.repositories.sql import (
    SqlJobEvaluationRepository, SqlJobRepository, SqlJobSourceRepository,
)
from backend.infrastructure.repositories.users import (
    SqlOutreachRepository, SqlRecruiterRepository, start_of_day,
)
from backend.observability import log_event


@dataclass(frozen=True)
class OutreachResult:
    recruiter_id: int
    recruiter_name: str
    status: str  # sent | failed | skipped
    detail: str | None = None


class OutreachService:
    def __init__(self, *, recruiters: SqlRecruiterRepository, outreach: SqlOutreachRepository,
                 jobs: SqlJobRepository, sources: SqlJobSourceRepository,
                 evaluations: SqlJobEvaluationRepository, sender: EmailSender, daily_limit: int,
                 base_url: str, clock: Callable[[], datetime]):
        self._recruiters = recruiters
        self._outreach = outreach
        self._jobs = jobs
        self._sources = sources
        self._evaluations = evaluations
        self._sender = sender
        self._daily_limit = daily_limit
        self._base_url = base_url
        self._clock = clock

    def status(self, user: User, job_id: int) -> list[OutreachResult]:
        done = self._outreach.statuses(user.id, job_id)
        return [OutreachResult(r.id, r.name, done[r.id][0] if r.id in done else "not_sent")
                for r in self._recruiters.list_for_user(user.id)]

    def send(self, user: User, job_id: int) -> list[OutreachResult]:
        try:
            job = self._jobs.get(job_id)
        except LookupError as exc:
            raise AccountError("not_found") from exc
        if not user.email_verified:
            raise AccountError("email_not_verified")  # Reply-To must be an address the user owns
        recruiters = self._recruiters.list_for_user(user.id)
        if not recruiters:
            raise AccountError("no_recruiters")

        now = self._clock()
        already = self._outreach.statuses(user.id, job_id)
        budget = self._daily_limit - self._outreach.sent_count_since(user.id, start_of_day(now))
        evaluation = self._evaluations.latest_for_job(job_id)
        sources = self._sources.list_for_job(job_id)
        job_url = sources[0].source_url if sources else f"{self._base_url.rstrip('/')}/jobs/{job_id}"

        results = []
        for recruiter in recruiters:
            if already.get(recruiter.id, ("",))[0] == OutreachStatus.SENT.value:
                results.append(OutreachResult(recruiter.id, recruiter.name, "skipped", "already_sent"))
                continue
            if budget <= 0:
                results.append(OutreachResult(recruiter.id, recruiter.name, "skipped", "daily_limit"))
                continue
            email = render_outreach(
                recruiter_name=recruiter.name, sender_name=user.display_name, sender_email=user.email,
                job_title=job.title, job_company=job.client_company, job_url=job_url,
                is_government_tender=bool(evaluation and evaluation.is_government_tender),
            )
            try:
                self._sender.send(recruiter.email, email)
            except Exception as exc:  # noqa: BLE001 - record and continue with the next recruiter
                self._outreach.record(user.id, job_id, recruiter.id, OutreachStatus.FAILED, type(exc).__name__, now)
                results.append(OutreachResult(recruiter.id, recruiter.name, "failed", type(exc).__name__))
                continue
            self._outreach.record(user.id, job_id, recruiter.id, OutreachStatus.SENT, None, now)
            budget -= 1
            results.append(OutreachResult(recruiter.id, recruiter.name, "sent"))

        log_event("outreach_sent", logging.INFO, user_id=user.id, job_id=job_id,
                  sent=sum(r.status == "sent" for r in results), total=len(results))
        return results
