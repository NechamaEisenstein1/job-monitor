"""Login/logout, the personal area (profile, recruiters, matches, outreach), page-view tracking."""
from __future__ import annotations

import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from backend.api.deps import SESSION_COOKIE, CurrentUser, DbSession, csrf_protect
from backend.application.dto import AuthConfigDto, JobListDto, OutreachResultDto, RecruiterDto, UserDto
from backend.application.use_cases.accounts import AccountError, RecruiterInput
from backend.bootstrap import account_service, outreach_service, recruiter_service, utcnow, verification_service
from backend.domain.enums import ExperienceLevel
from backend.domain.models import User
from backend.domain.services.user_matching import recruiters_at
from backend.infrastructure.repositories.read_models import SqlReadRepository
from backend.infrastructure.repositories.sql import SqlJobRepository
from backend.infrastructure.oauth.google import OAuthError, PkcePair
from backend.infrastructure.repositories.users import DuplicateError, SqlAnalyticsRepository
from backend.observability import log_event

router = APIRouter(prefix="/api", dependencies=[Depends(csrf_protect)])

_ERROR_STATUS = {"invalid_credentials": 401, "too_many_attempts": 429, "not_found": 404,
                 "signup_disabled": 403, "email_not_verified": 403, "verification_recently_sent": 429}


def _fail(exc: AccountError) -> HTTPException:
    return HTTPException(status_code=_ERROR_STATUS.get(exc.code, 400), detail=exc.code)


def user_dto(user: User) -> UserDto:
    return UserDto(id=user.id, email=user.email, display_name=user.display_name, role=user.role.value,
                   is_admin=user.is_admin,
                   is_active=user.is_active, experience_level=user.experience_level.value,
                   alerts_enabled=user.alerts_enabled, created_at=user.created_at, last_login_at=user.last_login_at,
                   email_verified=user.email_verified, has_password=bool(user.password_hash),
                   google_linked=bool(user.google_sub))


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="lax", secure=request.app.state.settings.cookie_secure,
        max_age=request.app.state.cfg.users.session_days * 86400, path="/",
    )


# ------------------------------------------------------------------ auth

@router.get("/auth/config", response_model=AuthConfigDto)
def auth_config(request: Request) -> AuthConfigDto:
    """What the login screen should offer."""
    settings = request.app.state.settings
    return AuthConfigDto(signup_enabled=settings.allow_signup, google_enabled=request.app.state.google is not None,
                         contact_email=settings.contact_email)


class LoginIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=200)


@router.post("/auth/login", response_model=UserDto)
def login(body: LoginIn, request: Request, response: Response, session: DbSession) -> UserDto:
    try:
        user, token = account_service(session, request.app.state.cfg).login(body.email, body.password)
    except AccountError as exc:
        raise _fail(exc) from exc
    _set_session_cookie(request, response, token)
    return user_dto(user)


class RegisterIn(BaseModel):
    email: str = Field(max_length=320)
    display_name: str = Field(max_length=200)
    password: str = Field(max_length=200)
    experience_level: ExperienceLevel = ExperienceLevel.JUNIOR


@router.post("/auth/register", response_model=UserDto, status_code=201)
def register(body: RegisterIn, request: Request, response: Response, session: DbSession) -> UserDto:
    try:
        user, token = account_service(session, request.app.state.cfg).register(
            body.email, body.display_name, body.password, body.experience_level,
            allow_signup=request.app.state.settings.allow_signup)
    except AccountError as exc:
        raise _fail(exc) from exc
    except DuplicateError as exc:
        raise HTTPException(status_code=409, detail="duplicate_email") from exc
    _set_session_cookie(request, response, token)
    try:
        verification_service(session, request.app.state.settings, request.app.state.sender).send(user)
    except Exception as exc:  # noqa: BLE001 - the account exists; the user can resend from the personal area
        log_event("verification_email_failed", logging.ERROR, user_id=user.id, error=type(exc).__name__)
    return user_dto(user)


@router.post("/auth/verify/resend", status_code=204)
def resend_verification(user: CurrentUser, request: Request, session: DbSession) -> None:
    try:
        verification_service(session, request.app.state.settings, request.app.state.sender).send(user)
    except AccountError as exc:
        raise _fail(exc) from exc


@router.get("/auth/verify", include_in_schema=False)
def verify_email(request: Request, session: DbSession, token: Annotated[str, Query(max_length=100)] = "") -> RedirectResponse:
    user = verification_service(session, request.app.state.settings, request.app.state.sender).verify(token)
    return RedirectResponse(f"/me?verified={'1' if user else '0'}", status_code=303)


# ------------------------------------------------------------------ Google sign-in

OAUTH_COOKIE = "jm_oauth"
OAUTH_COOKIE_PATH = "/api/auth/google"


@router.get("/auth/google/start", include_in_schema=False)
def google_start(request: Request) -> RedirectResponse:
    google = request.app.state.google
    if google is None:
        raise HTTPException(status_code=404, detail="google_disabled")
    state, pkce = secrets.token_urlsafe(24), PkcePair.new()
    response = RedirectResponse(google.authorization_url(state, pkce), status_code=303)
    # state (anti-CSRF) and the PKCE verifier live only in this short, HttpOnly cookie.
    response.set_cookie(OAUTH_COOKIE, f"{state}.{pkce.verifier}", httponly=True, samesite="lax",
                        secure=request.app.state.settings.cookie_secure, max_age=600, path=OAUTH_COOKIE_PATH)
    return response


@router.get("/auth/google/callback", include_in_schema=False)
def google_callback(request: Request, session: DbSession, code: str = "", state: str = "",
                    error: str = "") -> RedirectResponse:
    google = request.app.state.google
    stored_state, _, verifier = (request.cookies.get(OAUTH_COOKIE) or "").partition(".")

    def done(target: str) -> RedirectResponse:
        response = RedirectResponse(target, status_code=303)
        response.delete_cookie(OAUTH_COOKIE, path=OAUTH_COOKIE_PATH)
        return response

    if google is None or error or not code or not stored_state or not secrets.compare_digest(stored_state, state):
        return done("/login?auth_error=google_failed")
    try:
        profile = google.fetch_profile(code, verifier)
        _, token, created = account_service(session, request.app.state.cfg).login_with_google(
            profile, allow_signup=request.app.state.settings.allow_signup)
    except OAuthError as exc:
        log_event("google_login_failed", logging.WARNING, error=str(exc)[:200])
        return done("/login?auth_error=google_failed")
    except AccountError as exc:
        return done(f"/login?auth_error={exc.code}")
    # New accounts land in the personal area to pick junior/experienced and add recruiters.
    response = done("/me?welcome=1" if created else "/")
    _set_session_cookie(request, response, token)
    return response


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, session: DbSession) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        account_service(session, request.app.state.cfg).logout(token)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/auth/me", response_model=UserDto)
def me(user: CurrentUser) -> UserDto:
    return user_dto(user)


class PasswordIn(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(max_length=200)


@router.post("/auth/password", status_code=204)
def change_password(body: PasswordIn, user: CurrentUser, request: Request, session: DbSession) -> None:
    try:
        account_service(session, request.app.state.cfg).change_password(user, body.current_password, body.new_password)
    except AccountError as exc:
        raise _fail(exc) from exc


# ------------------------------------------------------------------ profile

class ProfileIn(BaseModel):
    display_name: str = Field(max_length=200)
    experience_level: ExperienceLevel
    alerts_enabled: bool


@router.put("/me/profile", response_model=UserDto)
def update_profile(body: ProfileIn, user: CurrentUser, request: Request, session: DbSession) -> UserDto:
    try:
        updated = account_service(session, request.app.state.cfg).update_profile(
            user, display_name=body.display_name, level=body.experience_level, alerts_enabled=body.alerts_enabled)
    except AccountError as exc:
        raise _fail(exc) from exc
    return user_dto(updated)


# ------------------------------------------------------------------ recruiters

class RecruiterIn(BaseModel):
    name: str = Field(max_length=200)
    email: str = Field(max_length=320)
    company: str = Field(max_length=300)


RecruiterId = Annotated[int, Path(ge=1)]


@router.get("/me/recruiters", response_model=list[RecruiterDto])
def list_recruiters(user: CurrentUser, session: DbSession) -> list[RecruiterDto]:
    return [RecruiterDto.model_validate(r) for r in recruiter_service(session).list(user)]


@router.post("/me/recruiters", response_model=RecruiterDto, status_code=201)
def add_recruiter(body: RecruiterIn, user: CurrentUser, session: DbSession) -> RecruiterDto:
    try:
        return RecruiterDto.model_validate(recruiter_service(session).add(user, RecruiterInput(**body.model_dump())))
    except AccountError as exc:
        raise _fail(exc) from exc
    except DuplicateError as exc:
        raise HTTPException(status_code=409, detail="duplicate_recruiter") from exc


@router.put("/me/recruiters/{recruiter_id}", response_model=RecruiterDto)
def update_recruiter(recruiter_id: RecruiterId, body: RecruiterIn, user: CurrentUser, session: DbSession) -> RecruiterDto:
    try:
        return RecruiterDto.model_validate(
            recruiter_service(session).update(user, recruiter_id, RecruiterInput(**body.model_dump())))
    except AccountError as exc:
        raise _fail(exc) from exc
    except DuplicateError as exc:
        raise HTTPException(status_code=409, detail="duplicate_recruiter") from exc


@router.delete("/me/recruiters/{recruiter_id}", status_code=204)
def delete_recruiter(recruiter_id: RecruiterId, user: CurrentUser, session: DbSession) -> None:
    try:
        recruiter_service(session).delete(user, recruiter_id)
    except AccountError as exc:
        raise _fail(exc) from exc


# ------------------------------------------------------------------ matches & outreach

@router.get("/me/matches", response_model=JobListDto)
def my_matches(
    user: CurrentUser, request: Request, session: DbSession,
    government: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> JobListDto:
    """Active jobs that fit the user's profile, best first, with their known recruiters."""
    cfg = request.app.state.cfg
    result = SqlReadRepository(session, request.app.state.cfg.signals).list_jobs(
        status="active", role_types=cfg.roles.eligible_types, location_matched=True, government=government,
        junior=True if user.experience_level == ExperienceLevel.JUNIOR else None,
        sort="relevance", page=page, page_size=page_size,
    )
    recruiters = recruiter_service(session).list(user)
    if recruiters:
        jobs = SqlJobRepository(session)
        for item in result.items:
            known = recruiters_at(jobs.get(item.id), item.recruitment_companies, recruiters)
            item.known_recruiters = [r.name for r in known]
    return result


JobId = Annotated[int, Path(ge=1)]


@router.get("/me/jobs/{job_id}/outreach", response_model=list[OutreachResultDto])
def outreach_status(job_id: JobId, user: CurrentUser, request: Request, session: DbSession) -> list[OutreachResultDto]:
    service = outreach_service(session, request.app.state.settings, request.app.state.cfg, request.app.state.sender)
    return [OutreachResultDto(**r.__dict__) for r in service.status(user, job_id)]


@router.post("/me/jobs/{job_id}/outreach", response_model=list[OutreachResultDto])
def send_outreach(job_id: JobId, user: CurrentUser, request: Request, session: DbSession) -> list[OutreachResultDto]:
    service = outreach_service(session, request.app.state.settings, request.app.state.cfg, request.app.state.sender)
    try:
        return [OutreachResultDto(**r.__dict__) for r in service.send(user, job_id)]
    except AccountError as exc:
        raise _fail(exc) from exc


# ------------------------------------------------------------------ analytics

class PageViewIn(BaseModel):
    path: str = Field(max_length=200, pattern=r"^/[^\s]*$")


@router.post("/analytics/page-view", status_code=204)
def page_view(body: PageViewIn, user: CurrentUser, session: DbSession) -> None:
    # Only the route pattern is stored (ids collapsed), never query strings.
    path = "/".join(":id" if part.isdigit() or len(part) == 36 else part for part in body.path.split("?")[0].split("/"))
    SqlAnalyticsRepository(session).record("page_view", user.id, path[:200], utcnow())

