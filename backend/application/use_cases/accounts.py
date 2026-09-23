"""Accounts, login sessions and the user's own recruiter directory."""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.domain.enums import ExperienceLevel
from backend.domain.models import Recruiter, User
from backend.infrastructure.email.renderer import render_verification
from backend.infrastructure.email.senders import EmailSender
from backend.infrastructure.repositories.users import (
    SqlAnalyticsRepository, SqlEmailTokenRepository, SqlRecruiterRepository, SqlSessionRepository,
    SqlUserRepository,
)
from backend.infrastructure.oauth.google import GoogleProfile
from backend.infrastructure.security import hash_password, new_session_token, token_hash, verify_password

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 10
MAX_FAILED_LOGINS = 8
FAILED_LOGIN_WINDOW = timedelta(minutes=15)
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")


class AccountError(Exception):
    """User-facing validation/auth failure. `code` is stable for the UI to translate."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _email(value: str) -> str:
    value = (value or "").strip().lower()
    if not EMAIL.match(value) or len(value) > 320:
        raise AccountError("invalid_email")
    return value


def _password(value: str) -> str:
    if len(value or "") < MIN_PASSWORD:
        raise AccountError("password_too_short")
    return value


def _text(value: str, code: str, max_len: int = 200) -> str:
    value = " ".join((value or "").split())
    if not value or len(value) > max_len:
        raise AccountError(code)
    return value


class AccountService:
    def __init__(self, users: SqlUserRepository, sessions: SqlSessionRepository,
                 analytics: SqlAnalyticsRepository, clock: Callable[[], datetime], session_days: int):
        self._users = users
        self._sessions = sessions
        self._analytics = analytics
        self._clock = clock
        self._session_ttl = timedelta(days=session_days)

    # ------------------------------------------------------------- sessions

    def login(self, email: str, password: str) -> tuple[User, str]:
        now = self._clock()
        user = self._users.by_email(email or "")
        if user and self._analytics.count("login_failed", now - FAILED_LOGIN_WINDOW, user.id) >= MAX_FAILED_LOGINS:
            raise AccountError("too_many_attempts")
        # Always run one scrypt so unknown emails (and Google-only accounts, which have no
        # password) take as long as wrong passwords.
        valid = verify_password(password or "", (user.password_hash if user else None) or _DUMMY_HASH)
        if not user or not user.password_hash or not valid or not user.is_active:
            self._analytics.record("login_failed", user.id if user else None, None, now)
            raise AccountError("invalid_credentials")
        return user, self._start_session(user, "login")

    def login_with_google(self, profile: GoogleProfile, *, allow_signup: bool) -> tuple[User, str, bool]:
        """Sign in by Google identity -> (user, session token, account was just created).
        Links to an existing account only when Google confirms the email is verified
        (otherwise anyone could claim an address they don't own)."""
        created = False
        user = self._users.by_google_sub(profile.sub)
        if user is None:
            existing = self._users.by_email(profile.email)
            if existing is not None:
                if not profile.email_verified:
                    raise AccountError("google_email_unverified")
                existing.google_sub = profile.sub
                existing.email_verified = True
                user = self._users.save(existing)
            elif not allow_signup:
                raise AccountError("signup_disabled")
            else:
                user = self._users.save(User(
                    id=None, email=_email(profile.email), display_name=_text(profile.name, "invalid_name"),
                    password_hash=None, is_admin=False, is_active=True, experience_level=ExperienceLevel.JUNIOR,
                    alerts_enabled=True, created_at=self._clock(), google_sub=profile.sub,
                    email_verified=profile.email_verified))
                created = True
                self._analytics.record("signup", user.id, None, self._clock())
        if not user.is_active:
            raise AccountError("invalid_credentials")
        return user, self._start_session(user, "login_google"), created

    def register(self, email: str, display_name: str, password: str, level: ExperienceLevel,
                 *, allow_signup: bool) -> tuple[User, str]:
        """Self sign-up. The account works at once; alerts/outreach wait for email verification."""
        if not allow_signup:
            raise AccountError("signup_disabled")
        user = self.create_user(email, display_name, password, level=level, email_verified=False)
        self._analytics.record("signup", user.id, None, self._clock())
        return user, self._start_session(user, "login")

    def _start_session(self, user: User, event: str) -> str:
        now = self._clock()
        token = new_session_token()
        self._sessions.add(token_hash(token), user.id, now, now + self._session_ttl)
        user.last_login_at = now
        self._users.save(user)
        self._analytics.record(event, user.id, None, now)
        return token

    def logout(self, token: str) -> None:
        self._sessions.delete(token_hash(token))

    def user_for_token(self, token: str | None) -> User | None:
        if not token:
            return None
        user_id = self._sessions.user_id_for(token_hash(token), self._clock())
        user = self._users.get(user_id) if user_id else None
        return user if user and user.is_active else None

    # ------------------------------------------------------------- accounts

    def create_user(self, email: str, display_name: str, password: str, *, is_admin: bool = False,
                    level: ExperienceLevel = ExperienceLevel.JUNIOR, email_verified: bool = True) -> User:
        """Admin/CLI-created accounts are trusted (verified); self sign-up passes False."""
        user = User(id=None, email=_email(email), display_name=_text(display_name, "invalid_name"),
                    password_hash=hash_password(_password(password)), is_admin=is_admin, is_active=True,
                    experience_level=level, alerts_enabled=True, created_at=self._clock(),
                    email_verified=email_verified)
        return self._users.save(user)

    def update_profile(self, user: User, *, display_name: str, level: ExperienceLevel, alerts_enabled: bool) -> User:
        user.display_name = _text(display_name, "invalid_name")
        user.experience_level = level
        user.alerts_enabled = alerts_enabled
        return self._users.save(user)

    def change_password(self, user: User, current: str, new: str) -> None:
        # Google-only accounts may add a password without a current one.
        if user.password_hash and not verify_password(current or "", user.password_hash):
            raise AccountError("invalid_credentials")
        user.password_hash = hash_password(_password(new))
        self._users.save(user)

    def admin_update(self, user_id: int, *, is_active: bool | None = None, is_admin: bool | None = None,
                     new_password: str | None = None, acting_admin: User) -> User:
        user = self._users.get(user_id)
        if user is None:
            raise AccountError("not_found")
        if user.id == acting_admin.id and (is_active is False or is_admin is False):
            raise AccountError("cannot_demote_self")
        if is_active is not None:
            user.is_active = is_active
        if is_admin is not None:
            user.is_admin = is_admin
        if new_password:
            user.password_hash = hash_password(_password(new_password))
        self._users.save(user)
        if new_password or is_active is False:
            self._sessions.delete_for_user(user.id)  # force re-login
        return user

    def list_users(self) -> list[User]:
        return self._users.list()


@dataclass(frozen=True)
class RecruiterInput:
    name: str
    email: str
    company: str


class RecruiterService:
    """A user's private contact list. Every call is scoped to the calling user."""

    def __init__(self, repo: SqlRecruiterRepository, clock: Callable[[], datetime]):
        self._repo = repo
        self._clock = clock

    def list(self, user: User) -> list[Recruiter]:
        return self._repo.list_for_user(user.id)

    def add(self, user: User, data: RecruiterInput) -> Recruiter:
        return self._repo.save(Recruiter(
            id=None, user_id=user.id, name=_text(data.name, "invalid_name"), email=_email(data.email),
            company=_text(data.company, "invalid_company", 300), created_at=self._clock()))

    def update(self, user: User, recruiter_id: int, data: RecruiterInput) -> Recruiter:
        recruiter = self._repo.get(user.id, recruiter_id)
        if recruiter is None:
            raise AccountError("not_found")
        recruiter.name = _text(data.name, "invalid_name")
        recruiter.email = _email(data.email)
        recruiter.company = _text(data.company, "invalid_company", 300)
        return self._repo.save(recruiter)

    def delete(self, user: User, recruiter_id: int) -> None:
        if not self._repo.delete(user.id, recruiter_id):
            raise AccountError("not_found")


VERIFY_PURPOSE = "verify_email"
VERIFY_TTL = timedelta(hours=48)
RESEND_COOLDOWN = timedelta(minutes=1)


class EmailVerificationService:
    """Proves a user owns their address before we email it alerts or use it as Reply-To."""

    def __init__(self, users: SqlUserRepository, tokens: SqlEmailTokenRepository, sender: EmailSender,
                 base_url: str, clock: Callable[[], datetime]):
        self._users = users
        self._tokens = tokens
        self._sender = sender
        self._base_url = base_url.rstrip("/")
        self._clock = clock

    def send(self, user: User) -> None:
        if user.email_verified:
            return
        now = self._clock()
        last = self._tokens.last_issued(user.id, VERIFY_PURPOSE)
        if last and now - last < RESEND_COOLDOWN:
            raise AccountError("verification_recently_sent")
        token = new_session_token()
        self._tokens.add(token_hash(token), user.id, VERIFY_PURPOSE, now, now + VERIFY_TTL)
        link = f"{self._base_url}/api/auth/verify?token={token}"
        self._sender.send(user.email, render_verification(user.display_name, link))

    def verify(self, token: str) -> User | None:
        user_id = self._tokens.consume(token_hash(token or ""), VERIFY_PURPOSE, self._clock())
        user = self._users.get(user_id) if user_id else None
        if user is None:
            return None
        user.email_verified = True
        return self._users.save(user)
