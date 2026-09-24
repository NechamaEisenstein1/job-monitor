"""Request-scoped dependencies: DB session, the logged-in user, admin/recruiter gates, CSRF check."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.bootstrap import account_service
from backend.domain.models import User

SESSION_COOKIE = "jm_session"
CSRF_HEADER = "X-Requested-With"


def db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


DbSession = Annotated[Session, Depends(db)]


def current_user(request: Request, session: DbSession) -> User:
    user = account_service(session, request.app.state.cfg).user_for_token(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="admin_only")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_recruiter(user: CurrentUser) -> User:
    if not user.can_post_jobs:
        raise HTTPException(status_code=403, detail="recruiter_only")
    return user


RecruiterUser = Annotated[User, Depends(require_recruiter)]


def csrf_protect(request: Request) -> None:
    """State-changing requests must carry a custom header. Browsers never add it to
    cross-site form posts, and the session cookie is SameSite=Lax."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.headers.get(CSRF_HEADER) != "fetch":
        raise HTTPException(status_code=403, detail="csrf_header_missing")
