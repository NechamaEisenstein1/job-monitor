from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta
from enum import Enum

from backend.application.dto import DigestItem
from backend.application.ports import NotificationRepository
from backend.config.settings import EmailConfig
from backend.infrastructure.email.renderer import render_digest
from backend.infrastructure.email.senders import EmailSender
from backend.observability import log_event


class NotificationOutcome(Enum):
    SENT = "sent"
    SKIPPED_NO_RECIPIENT = "skipped_no_recipient"
    SKIPPED_NO_ITEMS = "skipped_no_items"
    SKIPPED_ALREADY_SENT = "skipped_already_sent"
    FAILED = "failed"


class NotificationService:
    """Daily digest with idempotency keyed on (notification_type, scheduled_date, recipient).
    Never keyed on 'did another run happen today'."""

    def __init__(self, repo: NotificationRepository, sender: EmailSender, cfg: EmailConfig,
                 clock: Callable[[], datetime]):
        self._repo = repo
        self._sender = sender
        self._cfg = cfg
        self._clock = clock

    def send_daily_digest(self, scheduled_date: date, items: list[DigestItem],
                          run_id: str | None = None) -> NotificationOutcome:
        recipient = self._cfg.recipient.strip()
        kind = self._cfg.notification_type
        if not recipient:
            log_event("email_skipped", reason="no_recipient_configured")
            return NotificationOutcome.SKIPPED_NO_RECIPIENT
        if not items:
            log_event("email_skipped", reason="no_eligible_changes", scheduled_date=scheduled_date)
            return NotificationOutcome.SKIPPED_NO_ITEMS

        now = self._clock()
        stale_before = now - timedelta(minutes=self._cfg.claim_timeout_minutes)
        if not self._repo.try_claim(kind, scheduled_date, recipient, run_id, now, stale_before):
            log_event("email_skipped", reason="already_sent", scheduled_date=scheduled_date)
            return NotificationOutcome.SKIPPED_ALREADY_SENT

        try:
            self._sender.send(recipient, render_digest(items, scheduled_date, self._cfg.subject))
        except Exception as exc:  # noqa: BLE001 - any send failure must release the claim
            self._repo.release(kind, scheduled_date, recipient)
            log_event("email_failed", logging.ERROR, error=type(exc).__name__, scheduled_date=scheduled_date)
            return NotificationOutcome.FAILED

        self._repo.mark_sent(kind, scheduled_date, recipient, self._clock())
        log_event("email_sent", items=len(items), scheduled_date=scheduled_date)
        return NotificationOutcome.SENT
