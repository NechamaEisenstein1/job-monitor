"""Admin analytics: logins, traffic, delivery and system health."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from backend.application.dto import AdminStatsDto, DailyCountDto, NamedCountDto
from backend.domain.enums import JobStatus
from backend.infrastructure.repositories.read_models import SqlReadRepository
from backend.infrastructure.repositories.users import (
    SqlAlertRepository, SqlAnalyticsRepository, SqlOutreachRepository, SqlUserRepository, days_ago,
)

TREND_DAYS = 14


class AdminQueries:
    def __init__(self, *, read: SqlReadRepository, users: SqlUserRepository, analytics: SqlAnalyticsRepository,
                 alerts: SqlAlertRepository, outreach: SqlOutreachRepository, clock: Callable[[], datetime]):
        self._read = read
        self._users = users
        self._analytics = analytics
        self._alerts = alerts
        self._outreach = outreach
        self._clock = clock

    def stats(self) -> AdminStatsDto:
        now = self._clock()
        week = now - timedelta(days=7)
        trend_start = days_ago(now, TREND_DAYS - 1)
        counts = self._analytics.daily_counts(["login", "login_failed", "page_view"], trend_start)
        daily = []
        for offset in range(TREND_DAYS):
            day = (trend_start + timedelta(days=offset)).date()
            daily.append(DailyCountDto(
                day=day, logins=counts.get((day, "login"), 0),
                failed_logins=counts.get((day, "login_failed"), 0), page_views=counts.get((day, "page_view"), 0)))
        return AdminStatsDto(
            users_total=len(self._users.list()),
            users_active_7d=self._analytics.distinct_users("page_view", week),
            logins_7d=self._analytics.count("login", week),
            failed_logins_7d=self._analytics.count("login_failed", week),
            page_views_7d=self._analytics.count("page_view", week),
            alerts_sent_7d=self._alerts.count_since(week),
            outreach_sent_7d=self._outreach.count_since(week),
            jobs_active=self._read.count_jobs(JobStatus.ACTIVE),
            jobs_eligible=self._read.count_eligible_active_jobs(),
            government_tenders_active=self._read.count_active_tenders(),
            daily=daily,
            top_pages=[NamedCountDto(name=p, count=n) for p, n in self._analytics.top_paths(week)],
            jobs_by_source=[NamedCountDto(name=s, count=n) for s, n in self._read.count_active_by_source()],
            jobs_by_role=[NamedCountDto(name=r, count=n) for r, n in self._read.count_by_role()],
            recent_runs=self._read.list_runs(10),
        )
