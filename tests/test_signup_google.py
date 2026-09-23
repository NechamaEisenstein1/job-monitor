"""Self sign-up, email verification and Google sign-in."""
from __future__ import annotations

import re
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import pytest

from backend.infrastructure.oauth.google import GoogleProfile, OAuthError

from tests.conftest import PASSWORD


def register(client, email="new@example.com", level="junior"):
    return client.post("/api/auth/register", json={"email": email, "display_name": "נחמה", "password": PASSWORD,
                                                   "experience_level": level})


def verification_link(world, email):
    [mail] = [m for m in world.sender.to(email) if "אימות" in m.subject]
    return re.search(r"(/api/auth/verify\?token=[\w-]+)", mail.text).group(1)


# ------------------------------------------------------------------ sign-up & verification

def test_register_logs_in_and_sends_verification(world):
    client = world.client()
    response = register(client, level="experienced")
    assert response.status_code == 201
    me = client.get("/api/auth/me").json()
    assert me["email"] == "new@example.com" and me["experience_level"] == "experienced"
    assert me["email_verified"] is False and me["has_password"] is True
    assert verification_link(world, "new@example.com")


def test_duplicate_and_invalid_registration(world):
    client = world.client()
    assert register(client, email="junior@example.com").json()["detail"] == "duplicate_email"
    bad = client.post("/api/auth/register", json={"email": "x@example.com", "display_name": "x", "password": "short"})
    assert bad.json()["detail"] == "password_too_short"


def test_signup_can_be_disabled(world):
    world.app.state.settings = replace(world.app.state.settings, allow_signup=False)
    assert world.client().get("/api/auth/config").json()["signup_enabled"] is False
    assert register(world.client()).status_code == 403


def test_verification_link_verifies_once(world):
    client = world.client()
    register(client)
    link = verification_link(world, "new@example.com")
    first = client.get(link, follow_redirects=False)
    assert first.status_code == 303 and first.headers["location"] == "/me?verified=1"
    assert client.get("/api/auth/me").json()["email_verified"] is True
    assert client.get(link, follow_redirects=False).headers["location"] == "/me?verified=0"  # single use


def test_resend_is_rate_limited(world):
    client = world.client()
    register(client)
    assert client.post("/api/auth/verify/resend").json()["detail"] == "verification_recently_sent"


def test_unverified_user_gets_no_alerts_and_cannot_do_outreach(world):
    client = world.client()
    register(client)
    client.post("/api/me/recruiters", json={"name": "רותי", "email": "ruti@example.com", "company": "HMS"})
    world.run_day("day1")
    assert [m for m in world.sender.to("new@example.com") if "אימות" not in m.subject] == []  # no job alert
    job_id = client.get("/api/me/matches").json()["items"][0]["id"]
    assert client.post(f"/api/me/jobs/{job_id}/outreach").json()["detail"] == "email_not_verified"

    client.get(verification_link(world, "new@example.com"))
    world.run_day("day1")
    assert any("Junior Backend Developer" in m.text for m in world.sender.to("new@example.com"))


# ------------------------------------------------------------------ Google

class FakeGoogle:
    redirect_uri = "http://testserver/api/auth/google/callback"

    def __init__(self, profile: GoogleProfile | None = None, fail: bool = False):
        self.profile, self.fail, self.seen = profile, fail, []

    def authorization_url(self, state, pkce):
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}&code_challenge={pkce.challenge}"

    def fetch_profile(self, code, verifier):
        self.seen.append((code, verifier))
        if self.fail:
            raise OAuthError("boom")
        return self.profile


def google_login(world, profile, **fake):
    world.app.state.google = FakeGoogle(profile, **fake)
    client = world.client()
    start = client.get("/api/auth/google/start", follow_redirects=False)
    assert start.status_code == 303 and start.headers["location"].startswith("https://accounts.google.com/")
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    callback = client.get("/api/auth/google/callback", params={"code": "abc", "state": state}, follow_redirects=False)
    return client, callback


PROFILE = GoogleProfile(sub="g-123", email="nechama@gmail.com", email_verified=True, name="נחמה")


def test_google_disabled_by_default(world):
    assert world.client().get("/api/auth/config").json()["google_enabled"] is False
    assert world.client().get("/api/auth/google/start", follow_redirects=False).status_code == 404


def test_google_sign_up_creates_verified_account(world):
    client, callback = google_login(world, PROFILE)
    assert callback.headers["location"] == "/me?welcome=1"
    me = client.get("/api/auth/me").json()
    assert me["google_linked"] and me["email_verified"] and not me["has_password"]
    # PKCE: the verifier from the cookie reached the token exchange.
    assert world.app.state.google.seen[0][0] == "abc" and len(world.app.state.google.seen[0][1]) > 40
    # A returning Google user lands on the dashboard, same account.
    client2, again = google_login(world, PROFILE)
    assert again.headers["location"] == "/" and client2.get("/api/auth/me").json()["id"] == me["id"]


def test_google_links_existing_account_only_when_email_verified(world):
    same_email = replace(PROFILE, email="junior@example.com")
    client, callback = google_login(world, same_email)
    assert callback.headers["location"] == "/"
    assert client.get("/api/auth/me").json()["id"] == world.junior.id

    unverified = replace(PROFILE, sub="g-999", email="senior@example.com", email_verified=False)
    _, refused = google_login(world, unverified)
    assert refused.headers["location"] == "/login?auth_error=google_email_unverified"


def test_google_state_mismatch_is_rejected(world):
    world.app.state.google = FakeGoogle(PROFILE)
    client = world.client()
    client.get("/api/auth/google/start", follow_redirects=False)
    forged = client.get("/api/auth/google/callback", params={"code": "abc", "state": "attacker"}, follow_redirects=False)
    assert forged.headers["location"] == "/login?auth_error=google_failed"
    assert world.app.state.google.seen == []  # never exchanged the code
    assert client.get("/api/auth/me").status_code == 401


def test_google_errors_do_not_log_in(world):
    client, callback = google_login(world, PROFILE, fail=True)
    assert callback.headers["location"] == "/login?auth_error=google_failed"
    assert client.get("/api/auth/me").status_code == 401


def test_google_only_account_cannot_password_login_but_can_set_password(world):
    client, _ = google_login(world, PROFILE)
    assert world.client().post("/api/auth/login", json={"email": PROFILE.email, "password": ""}).status_code == 401
    assert client.post("/api/auth/password", json={"current_password": "", "new_password": PASSWORD}).status_code == 204
    assert world.client().post("/api/auth/login", json={"email": PROFILE.email, "password": PASSWORD}).status_code == 200


@pytest.mark.parametrize("allow", [False])
def test_google_sign_up_respects_disabled_signup(world, allow):
    world.app.state.settings = replace(world.app.state.settings, allow_signup=allow)
    _, callback = google_login(world, PROFILE)
    assert callback.headers["location"] == "/login?auth_error=signup_disabled"


# ------------------------------------------------------------------ designated admin email

@pytest.fixture
def admin_email(world):
    users = replace(world.app.state.cfg.users, admin_emails="Owner@Example.com, other@example.com")
    world.app.state.cfg = replace(world.app.state.cfg, users=users)
    return "owner@example.com"


def test_designated_email_becomes_admin_only_after_verification(world, admin_email, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", admin_email)  # the verification service reads config from disk
    client = world.client()
    register(client, email=admin_email)
    assert client.get("/api/auth/me").json()["is_admin"] is False  # unverified: anyone could type that email
    client.get(verification_link(world, admin_email))
    assert client.get("/api/auth/me").json()["is_admin"] is True


def test_designated_email_via_verified_google_is_admin_at_once(world, admin_email):
    client, _ = google_login(world, replace(PROFILE, email=admin_email))
    assert client.get("/api/auth/me").json()["is_admin"] is True


def test_other_emails_are_not_promoted(world, admin_email):
    client, _ = google_login(world, PROFILE)
    assert client.get("/api/auth/me").json()["is_admin"] is False


def test_existing_verified_account_is_promoted_on_next_login(world):
    users = replace(world.app.state.cfg.users, admin_emails="junior@example.com")
    world.app.state.cfg = replace(world.app.state.cfg, users=users)
    assert world.client("junior@example.com").get("/api/auth/me").json()["is_admin"] is True
