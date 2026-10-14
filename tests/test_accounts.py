"""Accounts, private recruiter directory, per-user alerts, outreach and admin analytics."""
from __future__ import annotations

from backend.config.settings import PROJECT_ROOT
from tests.conftest import PASSWORD


def recruiter(client, name="רותי", email="ruti@hms.example.com", company="HMS"):
    response = client.post("/api/me/recruiters", json={"name": name, "email": email, "company": company})
    assert response.status_code == 201, response.text
    return response.json()


# ------------------------------------------------------------------ auth

def test_login_sets_http_only_cookie_and_me_works(world):
    client = world.client()
    response = client.post("/api/auth/login", json={"email": "JUNIOR@example.com", "password": PASSWORD})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert client.get("/api/auth/me").json()["email"] == "junior@example.com"
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_wrong_password_and_lockout(world):
    client = world.client()
    for _ in range(8):
        assert client.post("/api/auth/login", json={"email": "junior@example.com", "password": "nope"}).status_code == 401
    # Even the right password is refused while locked.
    assert client.post("/api/auth/login", json={"email": "junior@example.com", "password": PASSWORD}).status_code == 429


def test_state_changing_requests_need_csrf_header(world):
    client = world.client("junior@example.com")
    client.headers.pop("X-Requested-With")
    assert client.post("/api/me/recruiters", json={"name": "a", "email": "a@b.co", "company": "x"}).status_code == 403


def test_password_is_hashed_not_stored(world):
    from sqlalchemy import select

    from backend.infrastructure.db.orm import UserRow
    with world.app.state.session_factory() as s:
        stored = s.scalars(select(UserRow.password_hash)).first()
    assert stored.startswith("scrypt$") and PASSWORD not in stored


# ------------------------------------------------------------------ recruiters are private

def test_recruiters_are_private_per_user(world):
    dana, yossi = world.client("junior@example.com"), world.client("senior@example.com")
    saved = recruiter(dana)
    assert [r["name"] for r in dana.get("/api/me/recruiters").json()] == ["רותי"]
    assert yossi.get("/api/me/recruiters").json() == []
    assert yossi.delete(f"/api/me/recruiters/{saved['id']}").status_code == 404
    assert yossi.put(f"/api/me/recruiters/{saved['id']}",
                     json={"name": "x", "email": "x@y.co", "company": "z"}).status_code == 404
    assert dana.post("/api/me/recruiters", json={"name": "b", "email": "ruti@hms.example.com",
                                                 "company": "HMS"}).status_code == 409
    assert dana.post("/api/me/recruiters", json={"name": "b", "email": "not-an-email",
                                                 "company": "HMS"}).status_code == 400


# ------------------------------------------------------------------ alerts

def test_alerts_follow_the_profile(world):
    junior_mail = world.sender.to("junior@example.com")
    senior_mail = world.sender.to("senior@example.com")
    assert len(junior_mail) == 1 and len(senior_mail) == 1
    # The junior profile only gets junior roles; "Senior" titles never reach Dana.
    assert "Senior" not in junior_mail[0].text
    assert world.sender.to("admin@example.com")  # admins are users too


def test_alerts_are_sent_once_per_job(world):
    before = len(world.sender.to("junior@example.com"))
    world.run_day("day1")  # same jobs again
    assert len(world.sender.to("junior@example.com")) == before


def test_failed_alert_is_retried_next_run(world):
    admin = world.client("admin@example.com")
    admin.post("/api/admin/users", json={"email": "late@example.com", "display_name": "מאוחר",
                                         "password": "another-long-password"})
    world.sender.fail_for.add("late@example.com")
    world.run_day("day1")
    assert world.sender.to("late@example.com") == []
    world.sender.fail_for.clear()
    world.run_day("day1")  # nothing was recorded for the failed send, so it goes out now
    assert "Junior Backend Developer" in world.sender.to("late@example.com")[0].text


def test_new_tech_junior_job_is_alerted(world):
    world.run_day("day2")  # day 2 adds "Junior Data Analyst" in Jerusalem, 0-1 years - a tech (data) role
    assert "Junior Data Analyst" in world.sender.to("junior@example.com")[-1].text


def test_matches_list_known_recruiters(world):
    dana = world.client("junior@example.com")
    recruiter(dana, company="HMS")
    items = dana.get("/api/me/matches").json()["items"]
    assert items and all(i["is_junior"] and i["role_type"] != "other" for i in items)
    assert any(i["known_recruiters"] == ["רותי"] for i in items if "HMS" in i["recruitment_companies"])


# ------------------------------------------------------------------ outreach

def test_outreach_sends_one_personal_email_per_recruiter(world):
    dana = world.client("junior@example.com")
    recruiter(dana, name="רותי", email="ruti@example.com")
    recruiter(dana, name="משה", email="moshe@example.com")
    job_id = dana.get("/api/me/matches").json()["items"][0]["id"]

    results = dana.post(f"/api/me/jobs/{job_id}/outreach").json()
    assert sorted(r["status"] for r in results) == ["sent", "sent"]
    ruti, moshe = world.sender.to("ruti@example.com")[0], world.sender.to("moshe@example.com")[0]
    assert ruti.text.startswith("שלום רותי,") and moshe.text.startswith("שלום משה,")
    assert ruti.reply_to == "junior@example.com"  # replies go to the user

    # Clicking again never re-sends.
    again = dana.post(f"/api/me/jobs/{job_id}/outreach").json()
    assert {r["detail"] for r in again} == {"already_sent"}
    assert len(world.sender.to("ruti@example.com")) == 1


def test_outreach_failure_can_be_retried(world):
    dana = world.client("junior@example.com")
    recruiter(dana, email="flaky@example.com")
    job_id = dana.get("/api/me/matches").json()["items"][0]["id"]
    world.sender.fail_for.add("flaky@example.com")
    assert dana.post(f"/api/me/jobs/{job_id}/outreach").json()[0]["status"] == "failed"
    world.sender.fail_for.clear()
    assert dana.post(f"/api/me/jobs/{job_id}/outreach").json()[0]["status"] == "sent"


def test_outreach_without_recruiters_is_rejected(world):
    dana = world.client("junior@example.com")
    job_id = dana.get("/api/jobs").json()["items"][0]["id"]
    assert dana.post(f"/api/me/jobs/{job_id}/outreach").json()["detail"] == "no_recruiters"


def test_outreach_daily_limit(world):
    from dataclasses import replace
    world.app.state.cfg = replace(world.app.state.cfg, users=replace(world.app.state.cfg.users, outreach_daily_limit=1))
    dana = world.client("junior@example.com")
    recruiter(dana, name="א", email="a@example.com")
    recruiter(dana, name="ב", email="b@example.com")
    job_id = dana.get("/api/jobs").json()["items"][0]["id"]
    statuses = sorted((r["status"], r["detail"]) for r in dana.post(f"/api/me/jobs/{job_id}/outreach").json())
    assert statuses == [("sent", None), ("skipped", "daily_limit")]


# ------------------------------------------------------------------ admin

def test_admin_only(world):
    assert world.client("junior@example.com").get("/api/admin/stats").status_code == 403
    admin = world.client("admin@example.com")
    admin.post("/api/analytics/page-view", json={"path": "/jobs/12"})
    stats = admin.get("/api/admin/stats").json()
    assert stats["users_total"] == 3 and stats["logins_7d"] >= 1
    assert {"name": "/jobs/:id", "count": 1} in stats["top_pages"]  # ids collapsed
    assert stats["jobs_by_role"] and stats["recent_runs"]


def test_admin_manages_users(world):
    admin = world.client("admin@example.com")
    created = admin.post("/api/admin/users", json={"email": "new@example.com", "display_name": "חדש",
                                                   "password": "another-long-password"})
    assert created.status_code == 201
    assert admin.post("/api/admin/users", json={"email": "new@example.com", "display_name": "x",
                                                "password": "another-long-password"}).status_code == 409
    assert admin.post("/api/admin/users", json={"email": "short@example.com", "display_name": "x",
                                                "password": "short"}).json()["detail"] == "password_too_short"
    # Deactivating ends the user's sessions immediately.
    dana = world.client("junior@example.com")
    assert admin.put(f"/api/admin/users/{world.junior.id}", json={"is_active": False}).status_code == 200
    assert dana.get("/api/auth/me").status_code == 401
    # An admin cannot lock themselves out.
    assert admin.put(f"/api/admin/users/{world.admin.id}", json={"is_admin": False}).status_code == 400


def test_alert_queries_do_not_grow_with_users(world):
    """Alerts load everything in a few queries up front: more users must not mean more SELECTs."""
    from sqlalchemy import Engine, event

    selects = {"n": 0}

    def count(conn, cursor, statement, *args):  # noqa: ANN001
        if statement.lstrip().upper().startswith("SELECT"):
            selects["n"] += 1

    def selects_for_run() -> int:
        selects["n"] = 0
        world.run_day("day1")  # nothing new: every user is checked, nobody is emailed
        return selects["n"]

    event.listen(Engine, "before_cursor_execute", count)
    try:
        baseline = selects_for_run()
        admin = world.client("admin@example.com")
        for i in range(5):
            admin.post("/api/admin/users", json={"email": f"u{i}@example.com", "display_name": "x",
                                                 "password": "another-long-password"})
        world.run_day("day1")  # the new users get their first (and only) alert
        assert selects_for_run() == baseline
    finally:
        event.remove(Engine, "before_cursor_execute", count)


def test_scheduled_run_sends_no_user_alerts_without_smtp(session_factory, tmp_path):
    """Without SMTP the emails would only be written to a local folder; they must not be
    recorded as sent, or the real email would never go out once SMTP is configured."""
    import asyncio

    from backend.bootstrap import pipeline_from_settings
    from backend.config.settings import Settings, SmtpSettings

    def alerts_enabled(smtp) -> bool:
        settings = Settings(database_url=str(session_factory.kw["bind"].url), config_dir=PROJECT_ROOT / "config",
                            email_outbox_dir=tmp_path, smtp=smtp, log_level="WARNING")

        async def build():
            async with pipeline_from_settings(settings) as pipeline:
                return pipeline._user_alerts is not None
        return asyncio.run(build())

    assert not alerts_enabled(None)
    assert alerts_enabled(SmtpSettings(host="smtp.example.com", port=587, user="u", password="p",
                                       sender="u@example.com", use_tls=True))


def test_alerts_go_out_only_on_alert_days(world, cfg):
    from datetime import date

    from backend.bootstrap import user_alert_service

    assert cfg.users.alert_weekdays == {6, 2}  # Sunday and Wednesday
    world.client("admin@example.com").post("/api/admin/users", json={
        "email": "new@example.com", "display_name": "חדשה", "password": "another-long-password"})
    with world.app.state.session_factory() as s:
        service = user_alert_service(s, world.app.state.settings, cfg, world.sender)
        assert service.send_for_run(world.run.id, date(2026, 9, 24)) == 0  # Thursday: nothing goes out
        assert world.sender.to("new@example.com") == []
        assert service.send_for_run(world.run.id, date(2026, 9, 27)) == 1  # Sunday: the new user's alert
        assert len(world.sender.to("new@example.com")) == 1


def test_alert_email_lists_at_most_max_jobs_and_links_the_rest():
    from datetime import date

    from backend.domain.services.user_matching import AlertItem
    from backend.infrastructure.email.renderer import render_user_alert

    items = [AlertItem(job_id=i, title=f"Job {i}", location="Jerusalem", client_company=None,
                       junior_score=i / 100, is_government_tender=False, source_urls=[], recruiter_names=[])
             for i in range(1, 16)]
    email = render_user_alert("דנה", items, date(2026, 9, 27), "משרות - {date}", "https://site.example", max_jobs=10)
    assert email.html.count("/jobs/") == 10
    assert "Job 15" in email.html and "Job 5<" not in email.html  # best (highest score) first
    assert "ועוד 5 משרות" in email.html and "https://site.example/me" in email.html
    assert "להפסקת ההתראות" in email.text


# ------------------------------------------------------------------ contact the site admin

def test_users_write_to_the_admin_who_reads_and_handles_them(world):
    dana, admin = world.client("junior@example.com"), world.client("admin@example.com")
    sent = dana.post("/api/me/contact", json={"category": "complaint", "subject": "  משרה לא רלוונטית ",
                                               "body": "המשרה כבר לא קיימת באתר של החברה"})
    assert sent.status_code == 201

    [message] = admin.get("/api/admin/messages").json()
    assert message["subject"] == "משרה לא רלוונטית" and message["category"] == "complaint"
    assert message["user_email"] == "junior@example.com" and message["handled_at"] is None

    assert admin.put(f"/api/admin/messages/{message['id']}", json={"handled": True}).status_code == 204
    assert admin.get("/api/admin/messages", params={"open_only": True}).json() == []
    assert admin.put(f"/api/admin/messages/{message['id']}", json={"handled": False}).status_code == 204
    assert len(admin.get("/api/admin/messages", params={"open_only": True}).json()) == 1
    assert admin.put("/api/admin/messages/9999", json={"handled": True}).status_code == 404


def test_contact_messages_are_private_validated_and_rate_limited(world):
    dana = world.client("junior@example.com")
    assert dana.get("/api/admin/messages").status_code == 403  # only admins read messages
    assert world.client().post("/api/me/contact", json={"category": "other", "subject": "x", "body": "y"}).status_code == 401
    assert dana.post("/api/me/contact", json={"category": "spam", "subject": "x", "body": "y"}).status_code == 422
    assert dana.post("/api/me/contact", json={"category": "other", "subject": "  ", "body": "y"}).status_code == 400
    assert dana.post("/api/me/contact", json={"category": "other", "subject": "x", "body": "y" * 5001}).status_code == 422
    for _ in range(5):
        assert dana.post("/api/me/contact", json={"category": "question", "subject": "x", "body": "y"}).status_code == 201
    assert dana.post("/api/me/contact", json={"category": "question", "subject": "x", "body": "y"}).status_code == 429
