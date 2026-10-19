"""Postings by users without the recruiter role (admin approval queue), users' "details are
correct" votes and the board's reliability filter / sort."""
from __future__ import annotations

from dataclasses import replace

from tests.test_recruiting import POSTING, _make_recruiter

SUBMISSION = {**POSTING, "tender_number": "S-1", "source_recruiter": "רחל כהן",
              "source_published_on": "2026-09-20"}


def _submit(client, **overrides):
    return client.post("/api/job-submissions", json={**SUBMISSION, **overrides})


def _board_ids(client, **params):
    return [i["id"] for i in client.get("/api/jobs", params={"page_size": 200, **params})
            .json()["items"]]


# ------------------------------------------------------------------ submissions

def test_submission_waits_for_admin_and_is_not_on_the_board(world):
    junior = world.client("junior@example.com")
    response = _submit(junior)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending" and body["job_id"] is None
    assert body["source_recruiter"] == "רחל כהן" and body["source_published_on"] == "2026-09-20"

    before = world.client("senior@example.com").get("/api/jobs", params={"q": "Python זוטר"}).json()
    assert before["total"] == 0
    assert [s["id"] for s in junior.get("/api/job-submissions/mine").json()] == [body["id"]]

    # The admin sees it with all its details and who sent it.
    admin = world.client("admin@example.com")
    queue = admin.get("/api/admin/job-submissions").json()
    assert [(q["id"], q["submitter_email"], q["description"]) for q in queue] == \
        [(body["id"], "junior@example.com", POSTING["description"])]


def test_approve_publishes_with_source_and_awards_the_submitter(world):
    junior = world.client("junior@example.com")
    submission_id = _submit(junior).json()["id"]
    admin = world.client("admin@example.com")
    result = admin.post(f"/api/admin/job-submissions/{submission_id}/approve")
    assert result.status_code == 200
    assert result.json()["points_awarded"] == 10
    job_id = result.json()["submission"]["job_id"]

    detail = world.client("senior@example.com").get(f"/api/jobs/{job_id}").json()
    assert detail["is_manual"] and detail["tender_number"] == "S-1"
    assert detail["source_recruiter"] == "רחל כהן" and detail["source_published_on"] == "2026-09-20"
    assert junior.get("/api/billing/wallet").json()["balance"] == 10
    assert [j["id"] for j in junior.get("/api/recruiter/jobs").json()] == [job_id]
    assert junior.get("/api/job-submissions/mine").json()[0]["status"] == "approved"
    assert admin.get("/api/admin/job-submissions").json() == []
    # Reviewed once only.
    again = admin.post(f"/api/admin/job-submissions/{submission_id}/approve")
    assert again.status_code == 409 and again.json()["detail"] == "already_reviewed"


def test_reject_keeps_it_off_the_board_and_tells_the_submitter(world):
    junior = world.client("junior@example.com")
    submission_id = _submit(junior).json()["id"]
    admin = world.client("admin@example.com")
    rejected = admin.post(f"/api/admin/job-submissions/{submission_id}/reject", json={"note": "המכרז נסגר"})
    assert rejected.status_code == 200 and rejected.json()["submission"]["job_id"] is None
    mine = junior.get("/api/job-submissions/mine").json()[0]
    assert (mine["status"], mine["review_note"]) == ("rejected", "המכרז נסגר")
    assert world.client("senior@example.com").get("/api/jobs", params={"q": "Python זוטר"}).json()["total"] == 0


def test_only_admins_review(world):
    junior = world.client("junior@example.com")
    submission_id = _submit(junior).json()["id"]
    assert junior.get("/api/admin/job-submissions").status_code == 403
    assert junior.post(f"/api/admin/job-submissions/{submission_id}/approve").status_code == 403
    recruiter = _make_recruiter(world, world.senior)
    assert recruiter.post(f"/api/admin/job-submissions/{submission_id}/reject", json={}).status_code == 403


def test_submission_requires_source_and_is_validated(world):
    junior = world.client("junior@example.com")
    assert _submit(junior, source_recruiter="  ").json()["detail"] == "invalid_source_recruiter"
    assert _submit(junior, source_published_on=None).json()["detail"] == "invalid_source_published_on"
    assert _submit(junior, source_published_on="2030-01-01").json()["detail"] == "invalid_source_published_on"
    assert _submit(junior, title=" ").json()["detail"] == "invalid_title"
    # Regular users still cannot publish directly.
    assert junior.post("/api/recruiter/jobs", json=POSTING).status_code == 403


def test_duplicate_tender_number_and_daily_limit(world):
    world.app.state.cfg = replace(world.app.state.cfg,
                                  billing=replace(world.app.state.cfg.billing, max_submissions_per_day=2))
    junior = world.client("junior@example.com")
    assert _submit(junior).status_code == 201
    duplicate = _submit(world.client("senior@example.com"))
    assert duplicate.status_code == 409 and duplicate.json()["detail"] == "duplicate_tender_number"
    assert _submit(junior, tender_number="S-2").status_code == 201
    limited = _submit(junior, tender_number="S-3")
    assert limited.status_code == 429 and limited.json()["detail"] == "submission_limit"


# ------------------------------------------------------------------ verification votes & reliability

def test_votes_raise_reliability_and_drive_filter_and_sort(world):
    recruiter = _make_recruiter(world, world.junior)
    job_id = recruiter.post("/api/recruiter/jobs", json=POSTING).json()["job"]["id"]
    senior, admin = world.client("senior@example.com"), world.client("admin@example.com")

    assert job_id not in _board_ids(senior, reliability="medium")
    voted = senior.put(f"/api/jobs/{job_id}/verification")
    assert voted.json() == {"verification_count": 1, "reliability": "medium"}
    assert senior.put(f"/api/jobs/{job_id}/verification").json()["verification_count"] == 1  # once per user
    assert admin.put(f"/api/jobs/{job_id}/verification").json()["verification_count"] == 2
    assert senior.get("/api/me/verifications").json() == [job_id]

    assert _board_ids(senior, reliability="medium") == [job_id]
    assert _board_ids(senior, reliability="high") == []
    assert _board_ids(senior, sort="reliability")[0] == job_id
    item = senior.get("/api/jobs", params={"q": "Python זוטר"}).json()["items"][0]
    assert (item["verification_count"], item["reliability"]) == (2, "medium")
    assert senior.get(f"/api/jobs/{job_id}").json()["verification_count"] == 2

    assert senior.delete(f"/api/jobs/{job_id}/verification").json()["verification_count"] == 1
    assert senior.get("/api/me/verifications").json() == []


def test_poster_cannot_vouch_for_own_posting_and_votes_go_with_the_job(world):
    recruiter = _make_recruiter(world, world.junior)
    job_id = recruiter.post("/api/recruiter/jobs", json=POSTING).json()["job"]["id"]
    own = recruiter.put(f"/api/jobs/{job_id}/verification")
    assert own.status_code == 403 and own.json()["detail"] == "own_posting"
    senior = world.client("senior@example.com")
    assert senior.get(f"/api/jobs/{job_id}").json()["posted_by"] == world.junior.id  # the UI hides the button
    assert senior.put("/api/jobs/999999/verification").status_code == 404
    senior.put(f"/api/jobs/{job_id}/verification")
    assert recruiter.delete(f"/api/recruiter/jobs/{job_id}").status_code == 200
    assert senior.get("/api/me/verifications").json() == []
