"""Connect the user's Gmail (send-only permission) and the read-tracking image."""
from __future__ import annotations

import base64
import logging
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from backend.api.deps import CurrentUser, DbSession, csrf_protect, current_user
from backend.application.dto import GmailStatusDto
from backend.bootstrap import utcnow
from backend.infrastructure.oauth.google import OAuthError, PkcePair
from backend.infrastructure.repositories.users import SqlGmailRepository, SqlOutreachRepository
from backend.observability import log_event

router = APIRouter(prefix="/api")

GMAIL_COOKIE = "jm_gmail_oauth"
GMAIL_COOKIE_PATH = "/api/gmail"
# Loads within this window after sending are the sender's own preview or a link scanner.
IGNORE_OPENS_WITHIN = timedelta(seconds=60)
# Smallest transparent GIF.
PIXEL = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


@router.get("/gmail/status", response_model=GmailStatusDto)
def gmail_status(user: CurrentUser, request: Request, session: DbSession) -> GmailStatusDto:
    available = request.app.state.gmail is not None
    connection = SqlGmailRepository(session).get(user.id) if available else None
    return GmailStatusDto(available=available, connected=connection is not None,
                          email=connection.google_email if connection else None,
                          connected_at=connection.connected_at if connection else None)


@router.get("/gmail/connect", include_in_schema=False)
def gmail_connect(user: CurrentUser, request: Request) -> RedirectResponse:
    gmail = request.app.state.gmail
    if gmail is None:
        raise HTTPException(status_code=404, detail="gmail_disabled")
    state, pkce = secrets.token_urlsafe(24), PkcePair.new()
    response = RedirectResponse(gmail.authorization_url(state, pkce, login_hint=user.email), status_code=303)
    response.set_cookie(GMAIL_COOKIE, f"{state}.{pkce.verifier}", httponly=True, samesite="lax",
                        secure=request.app.state.settings.cookie_secure, max_age=600, path=GMAIL_COOKIE_PATH)
    return response


@router.get("/gmail/callback", include_in_schema=False)
def gmail_callback(request: Request, session: DbSession, code: str = "", state: str = "",
                   error: str = "") -> RedirectResponse:
    stored_state, _, verifier = (request.cookies.get(GMAIL_COOKIE) or "").partition(".")

    def done(result: str) -> RedirectResponse:
        response = RedirectResponse(f"/me?gmail={result}", status_code=303)
        response.delete_cookie(GMAIL_COOKIE, path=GMAIL_COOKIE_PATH)
        return response

    gmail, cipher = request.app.state.gmail, request.app.state.cipher
    try:
        user = current_user(request, session)  # the connection belongs to whoever is logged in
    except HTTPException:
        return done("failed")
    if gmail is None or error or not code or not stored_state or not secrets.compare_digest(stored_state, state):
        return done("denied" if error == "access_denied" else "failed")
    try:
        grant = gmail.exchange(code, verifier)
    except OAuthError as exc:
        log_event("gmail_connect_failed", logging.WARNING, user_id=user.id, error=str(exc)[:200])
        return done("no_permission" if "gmail.send" in str(exc) else "failed")
    SqlGmailRepository(session).save(user.id, grant.email, cipher.encrypt(grant.refresh_token), grant.scopes, utcnow())
    log_event("gmail_connected", user_id=user.id)
    return done("connected")


@router.post("/gmail/disconnect", status_code=204, dependencies=[Depends(csrf_protect)])
def gmail_disconnect(user: CurrentUser, request: Request, session: DbSession) -> None:
    repo = SqlGmailRepository(session)
    connection = repo.get(user.id)
    if connection is None:
        return
    gmail, cipher = request.app.state.gmail, request.app.state.cipher
    if gmail is not None and cipher is not None:
        try:
            gmail.revoke(cipher.decrypt(connection.refresh_token_enc))
        except OAuthError:
            pass  # undecryptable token: nothing to revoke, delete anyway
    repo.delete(user.id)


@router.get("/o/{token}.gif", include_in_schema=False)
def tracking_pixel(token: str, session: DbSession) -> Response:
    """Always the same image, whatever the token - reveals nothing to whoever loads it."""
    if 16 <= len(token) <= 64:
        SqlOutreachRepository(session).record_open(token, utcnow(), IGNORE_OPENS_WITHIN)
    return Response(PIXEL, media_type="image/gif", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, private", "Pragma": "no-cache",
        "X-Robots-Tag": "noindex, nofollow"})
