"""'Send assistance request to recruiters': one personalised email per saved recruiter.

Safeguards: only the user's own recruiters; each (user, job, recruiter) is sent at most
once; a daily cap per user; replies go to the user (From: their Gmail, or Reply-To).

Read tracking: every email carries a 1x1 image with a random per-message token. When the
recruiter's mail client loads images, the open is recorded. It is a signal, not proof:
clients that block images never report an open, and some privacy features (Apple Mail)
load images without a human reading - the UI words it accordingly."""
from __future__ import annotations

import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from backend.application.use_cases.accounts import AccountError
from backend.domain.enums import OutreachStatus
from backend.domain.models import User
from backend.infrastructure.email.renderer import RenderedEmail, render_outreach
from backend.infrastructure.email.senders import EmailSender
from backend.infrastructure.oauth.gmail import GmailClient, GmailRevokedError, TokenCipher
from backend.infrastructure.repositories.sql import (
    SqlJobEvaluationRepository, SqlJobRepository, SqlJobSourceRepository,
)
from backend.infrastructure.repositories.users import (
    SqlGmailRepository, SqlOutreachRepository, SqlRecruiterRepository, start_of_day,
)
from backend.observability import log_event


@dataclass(frozen=True)
class OutreachResult:
    recruiter_id: int
    recruiter_name: str
    status: str  # sent | failed | skipped | not_sent
    detail: str | None = None
    sent_at: datetime | None = None
    sent_via: str | None = None  # gmail | site
    opened_at: datetime | None = None
    open_count: int = 0


def tracking_pixel_url(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/api/o/{token}.gif"


def with_tracking_pixel(email: RenderedEmail, pixel_url: str) -> RenderedEmail:
    pixel = f'<img src="{pixel_url}" width="1" height="1" alt="" style="display:block;border:0;width:1px;height:1px">'
    html = email.html.replace("</body>", f"{pixel}</body>") if "</body>" in email.html else email.html + pixel
    return replace(email, html=html)


class OutreachService:
    def __init__(self, *, recruiters: SqlRecruiterRepository, outreach: SqlOutreachRepository,
                 jobs: SqlJobRepository, sources: SqlJobSourceRepository,
                 evaluations: SqlJobEvaluationRepository, sender: EmailSender, daily_limit: int,
                 base_url: str, clock: Callable[[], datetime], gmail: GmailClient | None = None,
                 gmail_connections: SqlGmailRepository | None = None, cipher: TokenCipher | None = None):
        self._recruiters = recruiters
        self._outreach = outreach
        self._jobs = jobs
        self._sources = sources
        self._evaluations = evaluations
        self._sender = sender
        self._daily_limit = daily_limit
        self._base_url = base_url
        self._clock = clock
        self._gmail = gmail
        self._connections = gmail_connections
        self._cipher = cipher

    def status(self, user: User, job_id: int) -> list[OutreachResult]:
        done = self._outreach.statuses(user.id, job_id)
        results = []
        for r in self._recruiters.list_for_user(user.id):
            record = done.get(r.id)
            if record is None:
                results.append(OutreachResult(r.id, r.name, "not_sent"))
            else:
                results.append(OutreachResult(r.id, r.name, record.status, sent_at=record.created_at,
                                              sent_via=record.sent_via, opened_at=record.opened_at,
                                              open_count=record.open_count))
        return results

    def _gmail_token(self, user: User) -> tuple[str, str] | None:
        """(google_email, refresh_token) when the user connected Gmail and it is usable."""
        if not (self._gmail and self._connections and self._cipher):
            return None
        connection = self._connections.get(user.id)
        if connection is None:
            return None
        try:
            return connection.google_email, self._cipher.decrypt(connection.refresh_token_enc)
        except GmailRevokedError:
            self._connections.delete(user.id)
            return None

    def send(self, user: User, job_id: int) -> list[OutreachResult]:
        try:
            job = self._jobs.get(job_id)
        except LookupError as exc:
            raise AccountError("not_found") from exc
        gmail = self._gmail_token(user)
        # Sending from the site needs a verified Reply-To; Gmail proves the address itself.
        if gmail is None and not user.email_verified:
            raise AccountError("email_not_verified")
        recruiters = self._recruiters.list_for_user(user.id)
        if not recruiters:
            raise AccountError("no_recruiters")

        now = self._clock()
        already = self._outreach.statuses(user.id, job_id)
        budget = self._daily_limit - self._outreach.sent_count_since(user.id, start_of_day(now))
        evaluation = self._evaluations.latest_for_job(job_id)
        sources = self._sources.list_for_job(job_id)
        job_url = sources[0].source_url if sources else f"{self._base_url.rstrip('/')}/jobs/{job_id}"
        sender_email = gmail[0] if gmail else user.email

        results = []
        for recruiter in recruiters:
            previous = already.get(recruiter.id)
            if previous and previous.status == OutreachStatus.SENT.value:
                results.append(OutreachResult(recruiter.id, recruiter.name, "skipped", "already_sent"))
                continue
            if budget <= 0:
                results.append(OutreachResult(recruiter.id, recruiter.name, "skipped", "daily_limit"))
                continue
            token = secrets.token_urlsafe(24)
            email = with_tracking_pixel(render_outreach(
                recruiter_name=recruiter.name, sender_name=user.display_name, sender_email=sender_email,
                job_title=job.title, job_company=job.client_company, job_url=job_url,
                is_government_tender=bool(evaluation and evaluation.is_government_tender),
            ), tracking_pixel_url(self._base_url, token))
            try:
                if gmail:
                    self._gmail.send(gmail[1], sender_name=user.display_name, sender_email=gmail[0],
                                     recipient=recruiter.email, email=replace(email, reply_to=None))
                else:
                    self._sender.send(recruiter.email, email)
            except GmailRevokedError:
                # Access withdrawn at Google: forget the connection; the user must reconnect.
                self._connections.delete(user.id)
                self._outreach.record(user.id, job_id, recruiter.id, OutreachStatus.FAILED, "gmail_disconnected", now)
                results.append(OutreachResult(recruiter.id, recruiter.name, "failed", "gmail_disconnected"))
                break
            except Exception as exc:  # noqa: BLE001 - record and continue with the next recruiter
                self._outreach.record(user.id, job_id, recruiter.id, OutreachStatus.FAILED, type(exc).__name__, now)
                results.append(OutreachResult(recruiter.id, recruiter.name, "failed", type(exc).__name__))
                continue
            via = "gmail" if gmail else "site"
            self._outreach.record(user.id, job_id, recruiter.id, OutreachStatus.SENT, None, now,
                                  sent_via=via, tracking_token=token)
            budget -= 1
            results.append(OutreachResult(recruiter.id, recruiter.name, "sent", sent_at=now, sent_via=via))

        log_event("outreach_sent", logging.INFO, user_id=user.id, job_id=job_id, via="gmail" if gmail else "site",
                  sent=sum(r.status == "sent" for r in results), total=len(results))
        return results
