"""Admin-only endpoints: analytics and user management."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from backend.api.account_routes import _fail, user_dto
from backend.api.deps import AdminUser, DbSession, csrf_protect
from backend.application.dto import AdminStatsDto, ContactMessagePageDto, UserDto
from backend.application.use_cases.accounts import AccountError
from backend.application.use_cases.admin import AdminQueries
from backend.bootstrap import account_service, utcnow
from backend.domain.enums import ExperienceLevel, UserRole
from backend.infrastructure.repositories.contact import SqlContactRepository
from backend.infrastructure.repositories.read_models import SqlReadRepository
from backend.infrastructure.repositories.users import (
    DuplicateError, SqlAlertRepository, SqlAnalyticsRepository, SqlOutreachRepository, SqlUserRepository,
)

router = APIRouter(prefix="/api/admin", dependencies=[Depends(csrf_protect)])


@router.get("/stats", response_model=AdminStatsDto)
def stats(_: AdminUser, session: DbSession) -> AdminStatsDto:
    return AdminQueries(
        read=SqlReadRepository(session), users=SqlUserRepository(session),
        analytics=SqlAnalyticsRepository(session), alerts=SqlAlertRepository(session),
        outreach=SqlOutreachRepository(session), clock=utcnow,
    ).stats()


@router.get("/users", response_model=list[UserDto])
def list_users(_: AdminUser, request: Request, session: DbSession) -> list[UserDto]:
    wallets = SqlUserRepository(session).billing_summary()
    return [user_dto(u).model_copy(update=dict(zip(("points_balance", "subscription_status"),
                                                   wallets.get(u.id, (0, "inactive")))))
            for u in account_service(session, request.app.state.cfg).list_users()]


class NewUserIn(BaseModel):
    email: str = Field(max_length=320)
    display_name: str = Field(max_length=200)
    password: str = Field(max_length=200)
    is_admin: bool = False
    experience_level: ExperienceLevel = ExperienceLevel.A


@router.post("/users", response_model=UserDto, status_code=201)
def create_user(body: NewUserIn, _: AdminUser, request: Request, session: DbSession) -> UserDto:
    try:
        user = account_service(session, request.app.state.cfg).create_user(
            body.email, body.display_name, body.password, is_admin=body.is_admin, level=body.experience_level)
    except AccountError as exc:
        raise _fail(exc) from exc
    except DuplicateError as exc:
        raise HTTPException(status_code=409, detail="duplicate_email") from exc
    return user_dto(user)


class UserUpdateIn(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    role: UserRole | None = None  # grant / revoke RECRUITER (or ADMIN)
    new_password: str | None = Field(default=None, max_length=200)


@router.put("/users/{user_id}", response_model=UserDto)
def update_user(user_id: Annotated[int, Path(ge=1)], body: UserUpdateIn, admin: AdminUser,
                request: Request, session: DbSession) -> UserDto:
    try:
        user = account_service(session, request.app.state.cfg).admin_update(
            user_id, is_active=body.is_active, is_admin=body.is_admin, role=body.role,
            new_password=body.new_password,
            acting_admin=admin)
    except AccountError as exc:
        raise _fail(exc) from exc
    return user_dto(user)


# ------------------------------------------------------------------ contact messages from users

@router.get("/messages", response_model=ContactMessagePageDto)
def list_messages(_: AdminUser, session: DbSession, open_only: bool = False,
                  page: Annotated[int, Query(ge=1)] = 1,
                  page_size: Annotated[int, Query(ge=1, le=100)] = 50) -> ContactMessagePageDto:
    return SqlContactRepository(session).list(open_only=open_only, page=page, page_size=page_size)


class MessageUpdateIn(BaseModel):
    handled: bool


@router.put("/messages/{message_id}", status_code=204)
def update_message(message_id: Annotated[int, Path(ge=1)], body: MessageUpdateIn, _: AdminUser,
                   session: DbSession) -> None:
    if not SqlContactRepository(session).set_handled(message_id, utcnow() if body.handled else None):
        raise HTTPException(status_code=404, detail="not found")


class MessageReplyIn(BaseModel):
    reply: str = Field(min_length=1, max_length=5000)


@router.put("/messages/{message_id}/reply", status_code=204)
def reply_to_message(message_id: Annotated[int, Path(ge=1)], body: MessageReplyIn, _: AdminUser,
                     session: DbSession) -> None:
    """The reply is shown to the user in the personal area (and marks the message handled)."""
    reply = body.reply.strip()
    if not reply:
        raise HTTPException(status_code=400, detail="contact_empty")
    if not SqlContactRepository(session).set_reply(message_id, reply, utcnow()):
        raise HTTPException(status_code=404, detail="not found")
