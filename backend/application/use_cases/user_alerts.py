"""Per-user job alerts, sent right after each run.

Each (user, job) is alerted at most once (user_job_alerts). The record is written only
after the email was sent, so a failed send is retried on the next run."""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime

from backend.config.settings import MatchingConfig
from backend.domain.models import JobEvaluation
from backend.domain.services.user_matching import AlertItem, matches_profile, recruiters_at
from backend.infrastructure.email.renderer import render_user_alert
from backend.infrastructure.email.senders import EmailSender
from backend.infrastructure.repositories.sql import (
    SqlJobEvaluationRepository, SqlJobRepository, SqlJobSourceRepository,
)
from backend.infrastructure.repositories.users import (
    SqlAlertRepository, SqlRecruiterRepository, SqlUserRepository,
)
from backend.observability import log_event


class UserAlertService:
    def __init__(self, *, users: SqlUserRepository, recruiters: SqlRecruiterRepository,
                 alerts: SqlAlertRepository, evaluations: SqlJobEvaluationRepository,
                 jobs: SqlJobRepository, sources: SqlJobSourceRepository, sender: EmailSender,
                 config: MatchingConfig, base_url: str, clock: Callable[[], datetime]):
        self._users = users
        self._recruiters = recruiters
        self._alerts = alerts
        self._evaluations = evaluations
        self._jobs = jobs
        self._sources = sources
        self._sender = sender
        self._cfg = config
        self._base_url = base_url
        self._clock = clock

    def send_for_run(self, run_id: str, scheduled_date: date) -> int:
        """Returns how many users were emailed."""
        evaluations = self._evaluations.list_for_run(run_id)
        emailed = 0
        for user in self._users.list_alert_recipients():
            items = self._items_for(user, evaluations)
            if not items:
                continue
            email = render_user_alert(user.display_name, items, scheduled_date,
                                      self._cfg.users.alert_subject, self._base_url)
            try:
                self._sender.send(user.email, email)
            except Exception as exc:  # noqa: BLE001 - one user's failure must not stop the others
                log_event("user_alert_failed", logging.ERROR, user_id=user.id, error=type(exc).__name__)
                continue
            self._alerts.record(user.id, [i.job_id for i in items], run_id, self._clock())
            log_event("user_alert_sent", user_id=user.id, jobs=len(items),
                      tenders=sum(i.is_government_tender for i in items))
            emailed += 1
        return emailed

    def _items_for(self, user, evaluations: list[JobEvaluation]) -> list[AlertItem]:  # noqa: ANN001
        already = self._alerts.alerted_job_ids(user.id)
        recruiters = self._recruiters.list_for_user(user.id)
        items = []
        for ev in evaluations:
            if ev.job_id in already or not matches_profile(ev, user.experience_level, self._cfg.roles.eligible_types):
                continue
            job = self._jobs.get(ev.job_id)
            sources = self._sources.list_for_job(ev.job_id)
            known = recruiters_at(job, [s.recruitment_company for s in sources], recruiters)
            items.append(AlertItem(
                job_id=job.id, title=job.title, location=job.location, client_company=job.client_company,
                junior_score=ev.junior_score, is_government_tender=ev.is_government_tender,
                source_urls=[s.source_url for s in sources], recruiter_names=[r.name for r in known],
            ))
        return items
