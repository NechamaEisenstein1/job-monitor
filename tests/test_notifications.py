from dataclasses import replace
from datetime import date, timedelta

import pytest

from backend.application.dto import DigestItem
from backend.application.services.notification import NotificationOutcome as O, NotificationService
from backend.infrastructure.repositories.sql import SqlNotificationRepository

from tests.conftest import NOW

ITEMS = [DigestItem(1, "Junior Dev", "Intel", "Jerusalem", 0.8, ["new"], ["https://x.com/1"])]
DAY = date(2026, 9, 23)


class FakeSender:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    def send(self, recipient, email):
        if self.fail:
            raise ConnectionError("smtp down")
        self.sent.append((recipient, email.subject))


@pytest.fixture
def make_service(cfg, session_factory):
    sessions = []

    def factory(sender, recipient="me@example.com"):
        session = session_factory()
        sessions.append(session)
        email_cfg = replace(cfg.email, recipient=recipient)
        return NotificationService(SqlNotificationRepository(session), sender, email_cfg, lambda: NOW)

    yield factory
    for s in sessions:
        s.close()


def test_first_send(make_service):
    sender = FakeSender()
    assert make_service(sender).send_daily_digest(DAY, ITEMS) == O.SENT
    assert sender.sent == [("me@example.com", "משרות חדשות - 2026-09-23")]


def test_duplicate_send_prevented(make_service):
    sender = FakeSender()
    make_service(sender).send_daily_digest(DAY, ITEMS)
    # A separate service/session simulates a second, independent run.
    assert make_service(sender).send_daily_digest(DAY, ITEMS) == O.SKIPPED_ALREADY_SENT
    assert len(sender.sent) == 1


def test_failed_send_can_retry(make_service):
    assert make_service(FakeSender(fail=True)).send_daily_digest(DAY, ITEMS) == O.FAILED
    sender = FakeSender()
    assert make_service(sender).send_daily_digest(DAY, ITEMS) == O.SENT
    assert len(sender.sent) == 1


def test_different_date_can_send(make_service):
    sender = FakeSender()
    make_service(sender).send_daily_digest(DAY, ITEMS)
    assert make_service(sender).send_daily_digest(DAY + timedelta(days=1), ITEMS) == O.SENT


def test_different_recipient_can_send(make_service):
    sender = FakeSender()
    make_service(sender).send_daily_digest(DAY, ITEMS)
    assert make_service(sender, recipient="other@example.com").send_daily_digest(DAY, ITEMS) == O.SENT


def test_abandoned_pending_claim_is_taken_over_only_when_stale(session_factory, make_service):
    with session_factory() as s:
        repo = SqlNotificationRepository(s)
        assert repo.try_claim("daily_digest", DAY, "me@example.com", None, NOW, NOW - timedelta(minutes=30))
    # Fresh claim held by "another process": blocked.
    assert make_service(FakeSender()).send_daily_digest(DAY, ITEMS) == O.SKIPPED_ALREADY_SENT
    with session_factory() as s:
        repo = SqlNotificationRepository(s)
        assert repo.try_claim("daily_digest", DAY, "me@example.com", None, NOW + timedelta(hours=1), NOW + timedelta(minutes=1))


def test_skips_without_recipient_or_items(make_service):
    assert make_service(FakeSender(), recipient="").send_daily_digest(DAY, ITEMS) == O.SKIPPED_NO_RECIPIENT
    assert make_service(FakeSender()).send_daily_digest(DAY, []) == O.SKIPPED_NO_ITEMS
