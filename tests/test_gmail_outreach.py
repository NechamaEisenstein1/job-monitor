"""Sending outreach from the user's Gmail, and read tracking."""
from __future__ import annotations

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select, update

from backend.application.use_cases.outreach import with_tracking_pixel
from backend.infrastructure.db.orm import GmailConnectionRow, OutreachMessageRow
from backend.infrastructure.email.renderer import RenderedEmail
from backend.infrastructure.oauth.gmail import GmailGrant, GmailRevokedError, TokenCipher
from backend.infrastructure.oauth.google import OAuthError
from tests.test_accounts import recruiter

REFRESH = "1//refresh-token-secret"


class FakeGmail:
    """Stands in for Google: records sends, can simulate a revoked grant."""

    def __init__(self):
        self.sent: list[dict] = []
        self.revoked: list[str] = []
        self.revoke_on_send = False
        self.grant_scope_missing = False

    def authorization_url(self, state, pkce, login_hint):
        return f"https://accounts.google.test/auth?state={state}&login_hint={login_hint}"

    def exchange(self, code, verifier):
        if self.grant_scope_missing:
            raise OAuthError("gmail.send permission was not granted")
        return GmailGrant(email="dana.real@gmail.com", refresh_token=REFRESH, scopes="openid email gmail.send")

    def send(self, refresh_token, *, sender_name, sender_email, recipient, email):
        if self.revoke_on_send:
            raise GmailRevokedError("revoked")
        assert refresh_token == REFRESH
        self.sent.append({"from": sender_email, "to": recipient, "email": email})
        return "gmail-id"

    def revoke(self, refresh_token):
        self.revoked.append(refresh_token)


@pytest.fixture
def gmail(world):
    fake = FakeGmail()
    world.app.state.gmail = fake
    world.app.state.cipher = TokenCipher(Fernet.generate_key().decode())
    return fake


def connect(client) -> None:
    start = client.get("/api/gmail/connect", follow_redirects=False)
    assert start.status_code == 303
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    done = client.get("/api/gmail/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert done.headers["location"] == "/me?gmail=connected"


def _session(world):
    return world.app.state.session_factory()


def test_not_available_without_configuration(world):
    client = world.client("junior@example.com")
    assert client.get("/api/gmail/status").json() == {"available": False, "connected": False, "email": None,
                                                      "connected_at": None}
    assert client.get("/api/gmail/connect", follow_redirects=False).status_code == 404


def test_connect_stores_only_an_encrypted_token(world, gmail):
    client = world.client("junior@example.com")
    connect(client)
    status = client.get("/api/gmail/status").json()
    assert status["connected"] and status["email"] == "dana.real@gmail.com"
    with _session(world) as s:
        stored = s.get(GmailConnectionRow, world.junior.id).refresh_token_enc
    assert REFRESH not in stored and world.app.state.cipher.decrypt(stored) == REFRESH


def test_callback_rejects_forged_state_and_missing_permission(world, gmail):
    client = world.client("junior@example.com")
    client.get("/api/gmail/connect", follow_redirects=False)
    forged = client.get("/api/gmail/callback", params={"code": "c", "state": "wrong"}, follow_redirects=False)
    assert forged.headers["location"] == "/me?gmail=failed"
    gmail.grant_scope_missing = True
    start = client.get("/api/gmail/connect", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    no_scope = client.get("/api/gmail/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert no_scope.headers["location"] == "/me?gmail=no_permission"
    assert client.get("/api/gmail/status").json()["connected"] is False


def test_outreach_goes_from_gmail_with_a_tracking_image(world, gmail):
    dana = world.client("junior@example.com")
    connect(dana)
    recruiter(dana, name="רותי", email="ruti@example.com")
    job_id = dana.get("/api/me/matches").json()["items"][0]["id"]

    result = dana.post(f"/api/me/jobs/{job_id}/outreach").json()[0]
    assert result["status"] == "sent" and result["sent_via"] == "gmail"
    assert world.sender.to("ruti@example.com") == []  # not through the site's SMTP
    sent = gmail.sent[0]
    assert sent["from"] == "dana.real@gmail.com" and sent["to"] == "ruti@example.com"
    assert "/api/o/" in sent["email"].html and "/api/o/" not in sent["email"].text
    assert sent["email"].reply_to is None  # From is already her address


def test_open_is_recorded_but_not_right_after_sending(world, gmail):
    dana = world.client("junior@example.com")
    connect(dana)
    recruiter(dana, email="ruti@example.com")
    job_id = dana.get("/api/me/matches").json()["items"][0]["id"]
    dana.post(f"/api/me/jobs/{job_id}/outreach")
    with _session(world) as s:
        token = s.scalars(select(OutreachMessageRow.tracking_token)).one()

    anonymous = world.client()
    pixel = anonymous.get(f"/api/o/{token}.gif")
    assert pixel.headers["content-type"] == "image/gif" and "no-store" in pixel.headers["cache-control"]
    assert dana.get(f"/api/me/jobs/{job_id}/outreach").json()[0]["opened_at"] is None  # sender's own preview

    from backend.bootstrap import utcnow
    with _session(world) as s:  # pretend it was sent an hour ago
        s.execute(update(OutreachMessageRow).values(created_at=utcnow() - timedelta(hours=1)))
        s.commit()
    anonymous.get(f"/api/o/{token}.gif")
    anonymous.get(f"/api/o/{token}.gif")
    status = dana.get(f"/api/me/jobs/{job_id}/outreach").json()[0]
    assert status["opened_at"] and status["open_count"] == 2

    # Unknown tokens get the same image and change nothing.
    assert anonymous.get("/api/o/not-a-real-token-at-all.gif").status_code == 200


def test_revoked_gmail_disconnects_and_asks_to_reconnect(world, gmail):
    dana = world.client("junior@example.com")
    connect(dana)
    recruiter(dana, name="א", email="a@example.com")
    recruiter(dana, name="ב", email="b@example.com")
    gmail.revoke_on_send = True
    job_id = dana.get("/api/me/matches").json()["items"][0]["id"]
    results = dana.post(f"/api/me/jobs/{job_id}/outreach").json()
    assert [(r["status"], r["detail"]) for r in results] == [("failed", "gmail_disconnected")]  # stops at once
    assert dana.get("/api/gmail/status").json()["connected"] is False


def test_disconnect_revokes_at_google_and_deletes(world, gmail):
    dana = world.client("junior@example.com")
    connect(dana)
    assert dana.post("/api/gmail/disconnect").status_code == 204
    assert gmail.revoked == [REFRESH]
    assert dana.get("/api/gmail/status").json()["connected"] is False


def test_unverified_site_account_can_send_through_gmail(world, gmail):
    from backend.bootstrap import account_service
    with _session(world) as s:
        account_service(s, world.app.state.cfg).create_user("new@example.com", "חדשה", "correct-horse-battery",
                                                            email_verified=False)
    client = world.client("new@example.com")
    recruiter(client, email="ruti@example.com")
    job_id = client.get("/api/jobs").json()["items"][0]["id"]
    assert client.post(f"/api/me/jobs/{job_id}/outreach").json()["detail"] == "email_not_verified"
    connect(client)  # Gmail itself proves she owns the sending address
    assert client.post(f"/api/me/jobs/{job_id}/outreach").json()[0]["status"] == "sent"


def test_site_sent_outreach_is_tracked_too(world):
    dana = world.client("junior@example.com")
    recruiter(dana, email="ruti@example.com")
    job_id = dana.get("/api/me/matches").json()["items"][0]["id"]
    assert dana.post(f"/api/me/jobs/{job_id}/outreach").json()[0]["sent_via"] == "site"
    assert "/api/o/" in world.sender.to("ruti@example.com")[0].html


def test_pixel_goes_inside_body():
    email = with_tracking_pixel(RenderedEmail("s", "<html><body><p>x</p></body></html>", "x"), "https://t/p.gif")
    assert email.html.endswith('style="display:block;border:0;width:1px;height:1px"></body></html>')


# ------------------------------------------------------------------ the real client, against a mock Google

def _client_with(handler):
    import httpx

    from backend.infrastructure.oauth.gmail import GmailClient

    client = GmailClient("cid", "secret", "https://site.test/api/gmail/callback")
    client._http = lambda: httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_real_client_authorization_url_asks_for_send_only_and_offline():
    from backend.infrastructure.oauth.gmail import GmailClient
    from backend.infrastructure.oauth.google import PkcePair

    url = GmailClient("cid", "secret", "https://site.test/cb").authorization_url("st", PkcePair.new(), "d@x.com")
    query = parse_qs(urlparse(url).query)
    assert query["scope"] == ["openid email https://www.googleapis.com/auth/gmail.send"]
    assert query["access_type"] == ["offline"] and query["prompt"] == ["consent"]
    assert query["code_challenge_method"] == ["S256"] and query["login_hint"] == ["d@x.com"]


def test_real_client_refreshes_and_sends_mime_from_the_user():
    import base64
    import email
    import json

    import httpx

    seen = {}

    def google(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            assert b"grant_type=refresh_token" in request.content
            return httpx.Response(200, json={"access_token": "ya29.access"})
        assert request.headers["authorization"] == "Bearer ya29.access"
        seen["raw"] = json.loads(request.content)["raw"]
        return httpx.Response(200, json={"id": "m1"})

    rendered = RenderedEmail("בקשת סיוע", "<html><body><p>שלום</p></body></html>", "שלום")
    assert _client_with(google).send(REFRESH, sender_name="דנה", sender_email="dana@gmail.com",
                                     recipient="ruti@example.com", email=rendered) == "m1"
    message = email.message_from_bytes(base64.urlsafe_b64decode(seen["raw"]))
    assert message["To"] == "ruti@example.com" and "dana@gmail.com" in message["From"]
    assert {p.get_content_type() for p in message.walk()} >= {"text/plain", "text/html"}


def test_real_client_invalid_grant_means_revoked():
    import httpx

    def google(request):
        return httpx.Response(400, json={"error": "invalid_grant"})

    with pytest.raises(GmailRevokedError):
        _client_with(google).send(REFRESH, sender_name="d", sender_email="d@gmail.com", recipient="r@x.com",
                                  email=RenderedEmail("s", "<p>h</p>", "h"))


def test_outreach_log_lists_sent_emails_with_read_status(world, gmail):
    dana = world.client("junior@example.com")
    connect(dana)
    recruiter(dana, name="רותי", email="ruti@example.com")
    job = dana.get("/api/me/matches").json()["items"][0]
    dana.post(f"/api/me/jobs/{job['id']}/outreach")
    log = dana.get("/api/me/outreach").json()
    assert [(e["job_title"], e["recruiter_name"], e["status"], e["sent_via"], e["opened_at"]) for e in log] == \
        [(job["title"], "רותי", "sent", "gmail", None)]
    assert world.client("senior@example.com").get("/api/me/outreach").json() == []  # private to the user


def test_rate_limit_is_not_mistaken_for_revocation():
    import httpx

    def google(request):
        if request.url.path == "/token":
            return httpx.Response(200, json={"access_token": "a"})
        return httpx.Response(403, json={"error": {"message": "rateLimitExceeded"}})

    with pytest.raises(OAuthError) as caught:
        _client_with(google).send(REFRESH, sender_name="d", sender_email="d@gmail.com", recipient="r@x.com",
                                  email=RenderedEmail("s", "<p>h</p>", "h"))
    assert not isinstance(caught.value, GmailRevokedError)  # the connection is kept


def test_short_key_leaves_gmail_off():
    from backend.config.settings import PROJECT_ROOT, Settings

    base = dict(database_url="sqlite://", config_dir=PROJECT_ROOT / "config", email_outbox_dir=PROJECT_ROOT,
                smtp=None, log_level="WARNING", google_client_id="id", google_client_secret="secret")
    assert not Settings(**base, gmail_token_key="short").gmail_enabled
    assert Settings(**base, gmail_token_key="x" * 40).gmail_enabled
