"""Persistence for accounts, sessions, recruiters, alerts, outreach and analytics.
Every recruiter/outreach query is scoped by user_id - users never see each other's data."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.domain.enums import ExperienceLevel, OutreachStatus, UserRole
from backend.domain.models import Recruiter, User
from backend.infrastructure.db.orm import (
    AnalyticsEventRow, EmailTokenRow, OutreachMessageRow, RecruiterRow, UserJobAlertRow, UserRow, UserSessionRow,
)
from backend.infrastructure.repositories.mapping import to_domain, to_values

_USER_ENUMS = {"experience_level": ExperienceLevel, "role": UserRole}


class DuplicateError(Exception):
    pass


class SqlUserRepository:
    def __init__(self, session: Session):
        self._s = session

    def get(self, user_id: int) -> User | None:
        row = self._s.get(UserRow, user_id)
        return to_domain(row, User, _USER_ENUMS) if row else None

    def by_email(self, email: str) -> User | None:
        row = self._s.scalars(select(UserRow).where(func.lower(UserRow.email) == email.strip().lower())).first()
        return to_domain(row, User, _USER_ENUMS) if row else None

    def by_google_sub(self, sub: str) -> User | None:
        row = self._s.scalars(select(UserRow).where(UserRow.google_sub == sub)).first()
        return to_domain(row, User, _USER_ENUMS) if row else None

    def list(self) -> list[User]:
        return [to_domain(r, User, _USER_ENUMS) for r in self._s.scalars(select(UserRow).order_by(UserRow.id))]

    def billing_summary(self) -> dict[int, tuple[int, str]]:
        """user id -> (points balance, stored subscription status), for the admin list."""
        rows = self._s.execute(select(UserRow.id, UserRow.points_balance, UserRow.subscription_status))
        return {uid: (points, status) for uid, points, status in rows}

    def list_alert_recipients(self) -> list[User]:
        rows = self._s.scalars(select(UserRow).where(
            UserRow.is_active.is_(True), UserRow.alerts_enabled.is_(True), UserRow.email_verified.is_(True)))
        return [to_domain(r, User, _USER_ENUMS) for r in rows]

    def save(self, user: User) -> User:
        values = to_values(user)
        try:
            if user.id is None:
                row = UserRow(**values)
                self._s.add(row)
                self._s.flush()
                user.id = row.id
            else:
                row = self._s.get(UserRow, user.id)
                for key, value in values.items():
                    setattr(row, key, value)
                self._s.flush()
        except IntegrityError as exc:
            self._s.rollback()
            raise DuplicateError("email already registered") from exc
        self._s.commit()
        return user


class SqlSessionRepository:
    def __init__(self, session: Session):
        self._s = session

    def add(self, token_hash: str, user_id: int, now: datetime, expires_at: datetime) -> None:
        self._s.add(UserSessionRow(token_hash=token_hash, user_id=user_id, created_at=now, expires_at=expires_at))
        self._s.execute(delete(UserSessionRow).where(UserSessionRow.expires_at < now))  # housekeeping
        self._s.commit()

    def user_id_for(self, token_hash: str, now: datetime) -> int | None:
        row = self._s.get(UserSessionRow, token_hash)
        return row.user_id if row and row.expires_at > now else None

    def delete(self, token_hash: str) -> None:
        self._s.execute(delete(UserSessionRow).where(UserSessionRow.token_hash == token_hash))
        self._s.commit()

    def delete_for_user(self, user_id: int) -> None:
        self._s.execute(delete(UserSessionRow).where(UserSessionRow.user_id == user_id))
        self._s.commit()


class SqlEmailTokenRepository:
    def __init__(self, session: Session):
        self._s = session

    def add(self, token_hash: str, user_id: int, purpose: str, now: datetime, expires_at: datetime) -> None:
        # One live token per purpose: issuing a new link invalidates older ones.
        self._s.execute(delete(EmailTokenRow).where(EmailTokenRow.user_id == user_id, EmailTokenRow.purpose == purpose))
        self._s.add(EmailTokenRow(token_hash=token_hash, user_id=user_id, purpose=purpose,
                                  created_at=now, expires_at=expires_at))
        self._s.commit()

    def consume(self, token_hash: str, purpose: str, now: datetime) -> int | None:
        """Single use: returns the user id and deletes the token, or None if invalid/expired."""
        row = self._s.get(EmailTokenRow, token_hash)
        if row is None or row.purpose != purpose:
            return None
        user_id, valid = row.user_id, row.expires_at > now
        self._s.delete(row)
        self._s.commit()
        return user_id if valid else None

    def last_issued(self, user_id: int, purpose: str) -> datetime | None:
        return self._s.scalar(select(func.max(EmailTokenRow.created_at)).where(
            EmailTokenRow.user_id == user_id, EmailTokenRow.purpose == purpose))


class SqlRecruiterRepository:
    def __init__(self, session: Session):
        self._s = session

    def list_for_user(self, user_id: int) -> list[Recruiter]:
        rows = self._s.scalars(select(RecruiterRow).where(RecruiterRow.user_id == user_id).order_by(RecruiterRow.name))
        return [to_domain(r, Recruiter) for r in rows]

    def get(self, user_id: int, recruiter_id: int) -> Recruiter | None:
        row = self._s.get(RecruiterRow, recruiter_id)
        return to_domain(row, Recruiter) if row and row.user_id == user_id else None

    def save(self, recruiter: Recruiter) -> Recruiter:
        values = to_values(recruiter)
        try:
            if recruiter.id is None:
                row = RecruiterRow(**values)
                self._s.add(row)
                self._s.flush()
                recruiter.id = row.id
            else:
                row = self._s.get(RecruiterRow, recruiter.id)
                for key, value in values.items():
                    setattr(row, key, value)
                self._s.flush()
        except IntegrityError as exc:
            self._s.rollback()
            raise DuplicateError("a recruiter with this email already exists") from exc
        self._s.commit()
        return recruiter

    def delete(self, user_id: int, recruiter_id: int) -> bool:
        result = self._s.execute(
            delete(RecruiterRow).where(RecruiterRow.id == recruiter_id, RecruiterRow.user_id == user_id))
        self._s.commit()
        return result.rowcount > 0


class SqlAlertRepository:
    def __init__(self, session: Session):
        self._s = session

    def alerted_job_ids(self, user_id: int) -> set[int]:
        return set(self._s.scalars(select(UserJobAlertRow.job_id).where(UserJobAlertRow.user_id == user_id)))

    def record(self, user_id: int, job_ids: list[int], run_id: str | None, now: datetime) -> None:
        for job_id in job_ids:
            self._s.add(UserJobAlertRow(user_id=user_id, job_id=job_id, scrape_run_id=run_id, sent_at=now))
        self._s.commit()

    def count_since(self, since: datetime) -> int:
        return self._s.scalar(select(func.count()).select_from(UserJobAlertRow).where(UserJobAlertRow.sent_at >= since)) or 0


class SqlOutreachRepository:
    def __init__(self, session: Session):
        self._s = session

    def statuses(self, user_id: int, job_id: int) -> dict[int, tuple[str, datetime]]:
        rows = self._s.scalars(select(OutreachMessageRow).where(
            OutreachMessageRow.user_id == user_id, OutreachMessageRow.job_id == job_id))
        return {r.recruiter_id: (r.status, r.created_at) for r in rows}

    def sent_count_since(self, user_id: int, since: datetime) -> int:
        return self._s.scalar(select(func.count()).select_from(OutreachMessageRow).where(
            OutreachMessageRow.user_id == user_id, OutreachMessageRow.status == OutreachStatus.SENT.value,
            OutreachMessageRow.created_at >= since)) or 0

    def record(self, user_id: int, job_id: int, recruiter_id: int, status: OutreachStatus,
               error: str | None, now: datetime) -> None:
        """Upsert: a FAILED attempt may later be replaced by SENT; SENT is final."""
        row = self._s.scalars(select(OutreachMessageRow).where(
            OutreachMessageRow.user_id == user_id, OutreachMessageRow.job_id == job_id,
            OutreachMessageRow.recruiter_id == recruiter_id)).first()
        if row is None:
            self._s.add(OutreachMessageRow(user_id=user_id, job_id=job_id, recruiter_id=recruiter_id,
                                           status=status.value, error=error, created_at=now))
        else:
            row.status, row.error, row.created_at = status.value, error, now
        self._s.commit()

    def count_since(self, since: datetime) -> int:
        return self._s.scalar(select(func.count()).select_from(OutreachMessageRow).where(
            OutreachMessageRow.status == OutreachStatus.SENT.value, OutreachMessageRow.created_at >= since)) or 0


class SqlAnalyticsRepository:
    def __init__(self, session: Session):
        self._s = session

    def record(self, event_type: str, user_id: int | None, path: str | None, now: datetime) -> None:
        self._s.add(AnalyticsEventRow(event_type=event_type, user_id=user_id, path=path, created_at=now))
        self._s.commit()

    def count(self, event_type: str, since: datetime, user_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(AnalyticsEventRow).where(
            AnalyticsEventRow.event_type == event_type, AnalyticsEventRow.created_at >= since)
        if user_id is not None:
            stmt = stmt.where(AnalyticsEventRow.user_id == user_id)
        return self._s.scalar(stmt) or 0

    def daily_counts(self, event_types: list[str], since: datetime) -> dict[tuple[date, str], int]:
        day = func.date(AnalyticsEventRow.created_at)
        rows = self._s.execute(
            select(day, AnalyticsEventRow.event_type, func.count())
            .where(AnalyticsEventRow.event_type.in_(event_types), AnalyticsEventRow.created_at >= since)
            .group_by(day, AnalyticsEventRow.event_type))
        return {(d if isinstance(d, date) else date.fromisoformat(str(d)), t): n for d, t, n in rows}

    def distinct_users(self, event_type: str, since: datetime) -> int:
        return self._s.scalar(select(func.count(func.distinct(AnalyticsEventRow.user_id))).where(
            AnalyticsEventRow.event_type == event_type, AnalyticsEventRow.created_at >= since)) or 0

    def top_paths(self, since: datetime, limit: int = 8) -> list[tuple[str, int]]:
        rows = self._s.execute(
            select(AnalyticsEventRow.path, func.count().label("n"))
            .where(AnalyticsEventRow.event_type == "page_view", AnalyticsEventRow.created_at >= since)
            .group_by(AnalyticsEventRow.path).order_by(func.count().desc()).limit(limit))
        return [(p or "", n) for p, n in rows]


def start_of_day(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def days_ago(now: datetime, days: int) -> datetime:
    return start_of_day(now) - timedelta(days=days)
