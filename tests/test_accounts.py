"""Accounts, private recruiter directory, per-user alerts, outreach and admin analytics."""
from __future__ import annotations

from backend.config.settings import PROJECT_ROOT
import pytest

from tests.conftest import NOW, PASSWORD


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

    def alerts_enabled(smtp, **kw) -> bool:
        settings = Settings(database_url=str(session_factory.kw["bind"].url), config_dir=PROJECT_ROOT / "config",
                            email_outbox_dir=tmp_path, smtp=smtp, log_level="WARNING", **kw)

        async def build():
            async with pipeline_from_settings(settings) as pipeline:
                return pipeline._user_alerts is not None
        return asyncio.run(build())

    assert not alerts_enabled(None)
    assert alerts_enabled(SmtpSettings(host="smtp.example.com", port=587, user="u", password="p",
                                       sender="u@example.com", use_tls=True))
    assert alerts_enabled(None, brevo_api_key="key", email_from="site@example.com")


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

    listing = admin.get("/api/admin/messages").json()
    assert listing["total"] == 1 and listing["open_count"] == 1
    [message] = listing["items"]
    assert message["subject"] == "משרה לא רלוונטית" and message["category"] == "complaint"
    assert message["user_email"] == "junior@example.com" and message["handled_at"] is None

    assert admin.put(f"/api/admin/messages/{message['id']}", json={"handled": True}).status_code == 204
    assert admin.get("/api/admin/messages", params={"open_only": True}).json()["items"] == []
    assert admin.get("/api/admin/messages").json()["open_count"] == 0
    assert admin.put(f"/api/admin/messages/{message['id']}", json={"handled": False}).status_code == 204
    assert len(admin.get("/api/admin/messages", params={"open_only": True}).json()["items"]) == 1
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



def test_admin_messages_are_paged_and_the_open_count_covers_every_page(world):
    from datetime import timedelta

    from backend.bootstrap import utcnow
    from backend.infrastructure.repositories.contact import SqlContactRepository

    admin = world.client("admin@example.com")
    with world.app.state.session_factory() as s:
        repo, now = SqlContactRepository(s), utcnow()
        for i in range(7):  # oldest first, one per day so the daily limit never applies
            sent_at = now - timedelta(days=7 - i)
            assert repo.add_within_limit(world.junior.id, "question", f"m{i}", "x", sent_at,
                                         since=sent_at - timedelta(hours=12), limit=1)
    first = admin.get("/api/admin/messages", params={"page_size": 3}).json()
    assert [m["subject"] for m in first["items"]] == ["m6", "m5", "m4"]
    assert first["total"] == 7 and first["open_count"] == 7
    last = admin.get("/api/admin/messages", params={"page_size": 3, "page": 3}).json()
    assert [m["subject"] for m in last["items"]] == ["m0"]
    assert admin.get("/api/admin/messages", params={"page_size": 101}).status_code == 422


def test_users_see_their_own_messages_and_the_admins_reply(world):
    dana, yossi, admin = (world.client(e) for e in ("junior@example.com", "senior@example.com", "admin@example.com"))
    msg_id = dana.post("/api/me/contact", json={"category": "question", "subject": "שאלה", "body": "מתי?"}).json()["id"]
    yossi.post("/api/me/contact", json={"category": "other", "subject": "אחר", "body": "x"})

    mine = dana.get("/api/me/contact").json()["items"]
    assert [(m["subject"], m["reply"]) for m in mine] == [("שאלה", None)]  # never another user's

    assert dana.put(f"/api/admin/messages/{msg_id}/reply", json={"reply": "מחר"}).status_code == 403
    assert admin.put(f"/api/admin/messages/{msg_id}/reply", json={"reply": "  "}).status_code == 400
    assert admin.put("/api/admin/messages/9999/reply", json={"reply": "x"}).status_code == 404
    assert admin.put(f"/api/admin/messages/{msg_id}/reply", json={"reply": "מחר"}).status_code == 204

    mine = dana.get("/api/me/contact").json()["items"]
    assert mine[0]["reply"] == "מחר" and mine[0]["replied_at"]
    listed = {m["id"]: m for m in admin.get("/api/admin/messages").json()["items"]}
    assert listed[msg_id]["reply"] == "מחר" and listed[msg_id]["handled_at"]  # a reply marks it handled
    assert world.client().get("/api/me/contact").status_code == 401


def test_my_messages_are_paged_and_a_new_reply_comes_first(world):
    from datetime import timedelta

    from backend.bootstrap import utcnow
    from backend.infrastructure.repositories.contact import SqlContactRepository

    with world.app.state.session_factory() as s:
        repo, now = SqlContactRepository(s), utcnow()
        ids = []
        for i in range(12):  # oldest first, one per day so the daily limit never applies
            sent_at = now - timedelta(days=12 - i)
            ids.append(repo.add_within_limit(world.junior.id, "question", f"m{i}", "x", sent_at,
                                             since=sent_at - timedelta(hours=12), limit=1))
    dana, admin = world.client("junior@example.com"), world.client("admin@example.com")
    first = dana.get("/api/me/contact").json()
    assert first["total"] == 12 and first["page_size"] == 10 and first["items"][0]["subject"] == "m11"
    assert [m["subject"] for m in dana.get("/api/me/contact", params={"page": 2}).json()["items"]] == ["m1", "m0"]
    # Answering the oldest message brings it back to the top of the first page.
    assert admin.put(f"/api/admin/messages/{ids[0]}/reply", json={"reply": "סוף סוף"}).status_code == 204
    assert dana.get("/api/me/contact").json()["items"][0]["subject"] == "m0"


def test_personal_area_matches_default_to_ten_per_page(world):
    body = world.client("junior@example.com").get("/api/me/matches").json()
    assert body["page_size"] == 10


# ------------------------------------------------------------------ level A / B / C in the personal area

def test_matches_follow_the_users_level(world):
    dana, yossi = world.client("junior@example.com"), world.client("senior@example.com")  # levels A and B
    junior_matches = dana.get("/api/me/matches").json()["items"]
    assert junior_matches and all(j["is_junior"] for j in junior_matches)
    b_matches = yossi.get("/api/me/matches").json()["items"]
    assert b_matches and not any(j["is_junior"] for j in b_matches)  # experienced users no longer get junior jobs
    assert all(j["required_years"] is None or 2 < j["required_years"] <= 4 for j in b_matches)

    me = yossi.get("/api/auth/me").json()
    assert yossi.put("/api/me/profile", json={"display_name": me["display_name"], "experience_level": "c",
                                              "alerts_enabled": True}).status_code == 200
    c_matches = yossi.get("/api/me/matches").json()["items"]
    assert all(not j["is_junior"] and (j["required_years"] is None or j["required_years"] > 4) for j in c_matches)


@pytest.mark.parametrize("level, is_junior, years, expected", [
    ("a", True, None, True), ("a", False, None, False), ("a", True, 2, True),
    ("b", True, 1, False), ("b", False, 2.01, True), ("b", False, 4, True), ("b", False, 4.01, False),
    ("b", False, None, True), ("c", False, 4.01, True), ("c", False, 3, False), ("c", False, None, True),
])
def test_alert_matching_uses_the_same_levels(level, is_junior, years, expected):
    from backend.domain.enums import ExperienceLevel
    from backend.domain.models import JobEvaluation
    from backend.domain.services.user_matching import matches_profile
    ev = JobEvaluation(job_id=1, scrape_run_id="r", junior_score=0.5, is_eligible=True, matched_rules=[],
                       rejection_reasons=[], created_at=NOW, location_matched=True, role_type="software",
                       is_junior=is_junior, required_years=years)
    assert matches_profile(ev, ExperienceLevel(level), ["software"]) is expected


# ------------------------------------------------------------------ "I applied"

def test_applied_jobs_stay_listed_after_the_job_leaves_the_board(world):
    from backend.infrastructure.repositories.sql import SqlJobRepository

    dana, yossi = world.client("junior@example.com"), world.client("senior@example.com")
    job = dana.get("/api/jobs").json()["items"][0]
    assert dana.put(f"/api/me/applications/{job['id']}").status_code == 204
    assert dana.put(f"/api/me/applications/{job['id']}").status_code == 204  # twice = once
    assert dana.put("/api/me/applications/99999").status_code == 404
    [entry] = dana.get("/api/me/applications").json()
    assert entry["job_id"] == job["id"] and entry["title"] == job["title"] and entry["source_url"]
    assert yossi.get("/api/me/applications").json() == []  # private to each user

    with world.app.state.session_factory() as s:  # the daily refresh removes the job
        SqlJobRepository(s).delete_many([job["id"]])
        s.commit()
    [entry] = dana.get("/api/me/applications").json()
    assert entry["job_id"] is None and entry["job_removed"] and entry["title"] == job["title"]

    assert yossi.delete(f"/api/me/applications/entry/{entry['id']}").status_code == 404  # not hers
    assert dana.delete(f"/api/me/applications/entry/{entry['id']}").status_code == 204
    assert dana.get("/api/me/applications").json() == []


def test_unmarking_an_application(world):
    dana = world.client("junior@example.com")
    job_id = dana.get("/api/jobs").json()["items"][0]["id"]
    dana.put(f"/api/me/applications/{job_id}")
    assert dana.delete(f"/api/me/applications/{job_id}").status_code == 204
    assert dana.get("/api/me/applications").json() == []



def test_marking_a_job_that_disappears_meanwhile_reports_not_found(world, monkeypatch):
    """The daily refresh may delete the job between the lookup and the insert."""
    from backend.infrastructure.db.orm import JobRow
    from backend.infrastructure.repositories.applications import SqlApplicationRepository

    with world.app.state.session_factory() as s:
        repo, real_get = SqlApplicationRepository(s), s.get
        seen = {"n": 0}

        def get_once(cls, ident, *a, **kw):  # the first lookup still sees the job, then it is gone
            seen["n"] += 1
            return JobRow(id=ident, title="gone", status="active") if cls is JobRow and seen["n"] == 1 \
                else real_get(cls, ident, *a, **kw)

        monkeypatch.setattr(s, "get", get_once)
        assert repo.mark(world.junior.id, 99999, NOW) is False


# ------------------------------------------------------------------ preferred regions

def _profile(client, **changes):
    me = client.get("/api/auth/me").json()
    body = {"display_name": me["display_name"], "experience_level": me["experience_level"],
            "alerts_enabled": me["alerts_enabled"], **changes}
    return client.put("/api/me/profile", json=body)


def test_personal_area_follows_the_preferred_regions(world):
    dana = world.client("junior@example.com")
    assert [r["code"] for r in dana.get("/api/regions").json()][:2] == ["jerusalem", "center"]
    everywhere = {j["id"] for j in dana.get("/api/me/matches").json()["items"]}  # no regions picked = all of Israel

    assert _profile(dana, preferred_regions=["jerusalem"]).json()["preferred_regions"] == ["jerusalem"]
    jerusalem = dana.get("/api/me/matches").json()["items"]
    assert jerusalem and {j["id"] for j in jerusalem} <= everywhere
    assert all(any(p in (j["location"] or "") for p in ("ירושלים", "Jerusalem", "בית שמש")) for j in jerusalem)

    assert _profile(dana, preferred_regions=["south"]).status_code == 200
    assert dana.get("/api/me/matches").json()["items"] == []  # the demo jobs have none in the south
    assert _profile(dana).json()["preferred_regions"] == ["south"]  # not sent = unchanged
    assert _profile(dana, preferred_regions=[]).json()["preferred_regions"] == []
    assert _profile(dana, preferred_regions=["mars"]).status_code == 400


def test_alerts_use_the_preferred_regions(cfg):
    from backend.domain.enums import ExperienceLevel
    from backend.domain.models import JobEvaluation
    from backend.domain.services.user_matching import matches_profile
    ev = JobEvaluation(job_id=1, scrape_run_id="r", junior_score=0.5, is_eligible=True, matched_rules=[],
                       rejection_reasons=[], created_at=NOW, role_type="software", is_junior=True,
                       regions="|jerusalem|")
    assert matches_profile(ev, ExperienceLevel.A, ["software"])                         # all of Israel
    assert matches_profile(ev, ExperienceLevel.A, ["software"], regions=["center", "jerusalem"])
    assert not matches_profile(ev, ExperienceLevel.A, ["software"], regions=["center"])


def test_email_sender_choice(tmp_path, monkeypatch):
    """Brevo first (HTTPS, works where SMTP ports are blocked), then SMTP; a live site with
    neither refuses to send instead of quietly writing emails to a local folder."""
    import httpx

    from backend.bootstrap import build_email_sender
    from backend.config.settings import Settings, SmtpSettings
    from backend.infrastructure.email.renderer import RenderedEmail
    from backend.infrastructure.email.senders import (
        BrevoEmailSender, DisabledEmailSender, EmailNotConfiguredError, FileEmailSender, SmtpEmailSender,
    )

    def settings(**kw) -> Settings:
        return Settings(database_url="sqlite://", config_dir=PROJECT_ROOT / "config", email_outbox_dir=tmp_path,
                        log_level="WARNING", **{"smtp": None, **kw})

    smtp = SmtpSettings(host="smtp.example.com", port=587, user="u", password="p", sender="u@example.com", use_tls=True)
    assert isinstance(build_email_sender(settings()), FileEmailSender)
    live = settings(public_base_url="https://jobs.example.com")
    assert isinstance(build_email_sender(live), DisabledEmailSender) and not live.email_enabled
    email = RenderedEmail(subject="נושא", html="<p>שלום</p>", text="שלום", reply_to="me@example.com")
    with pytest.raises(EmailNotConfiguredError):
        build_email_sender(live).send("a@example.com", email)
    assert isinstance(build_email_sender(settings(smtp=smtp)), SmtpEmailSender)
    brevo = settings(smtp=smtp, brevo_api_key="key", email_from="site@example.com", email_from_name="מוניטור")
    assert brevo.email_enabled and isinstance(build_email_sender(brevo), BrevoEmailSender)

    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append((url, json, headers))
        return httpx.Response(201, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", fake_post)
    build_email_sender(brevo).send("a@example.com", email)
    [(url, body, headers)] = calls
    assert url == BrevoEmailSender.API_URL and headers["api-key"] == "key"
    assert body["sender"] == {"email": "site@example.com", "name": "מוניטור"}
    assert body["to"] == [{"email": "a@example.com"}] and body["replyTo"] == {"email": "me@example.com"}
    assert body["subject"] == "נושא" and body["htmlContent"] == "<p>שלום</p>" and body["textContent"] == "שלום"

    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Response(401, request=httpx.Request("POST", url)))
    with pytest.raises(httpx.HTTPStatusError):
        build_email_sender(brevo).send("a@example.com", email)
