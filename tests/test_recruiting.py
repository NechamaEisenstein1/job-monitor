"""Recruiter role, manual postings, the points ledger and subscriptions."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from backend.config.settings import PROJECT_ROOT, BillingConfig
from backend.domain.enums import SubscriptionStatus
from tests.conftest import NOW

POSTING = {"title": "מפתח/ת Python זוטר/ה", "description": "פיתוח מערכות מידע במשרד.\nללא ניסיון קודם.",
           "requirements": "תואר במדעי המחשב", "tender_number": "2026-117", "government_ministry": "משרד הבריאות",
           "location": "ירושלים"}


def _billing(world, **overrides):
    world.app.state.cfg = replace(world.app.state.cfg, billing=replace(world.app.state.cfg.billing, **overrides))


def _make_recruiter(world, user):
    admin = world.client("admin@example.com")
    response = admin.put(f"/api/admin/users/{user.id}", json={"role": "recruiter"})
    assert response.status_code == 200 and response.json()["role"] == "recruiter"
    return world.client(user.email)


def _post(client, **overrides):
    return client.post("/api/recruiter/jobs", json={**POSTING, **overrides})


# ------------------------------------------------------------------ roles & RBAC

def test_only_recruiters_and_admins_can_post(world):
    junior = world.client("junior@example.com")
    assert _post(junior).status_code == 403
    assert junior.get("/api/recruiter/jobs").status_code == 403
    assert _post(world.client("admin@example.com"), tender_number="A-1").status_code == 201


def test_only_admins_grant_roles_and_admin_cannot_demote_self(world):
    junior = world.client("junior@example.com")
    assert junior.put(f"/api/admin/users/{world.junior.id}", json={"role": "recruiter"}).status_code == 403
    admin = world.client("admin@example.com")
    assert admin.put(f"/api/admin/users/{world.admin.id}", json={"role": "recruiter"}).status_code == 400
    recruiter = _make_recruiter(world, world.junior)
    assert recruiter.get("/api/auth/me").json()["role"] == "recruiter"
    # revoke
    assert admin.put(f"/api/admin/users/{world.junior.id}", json={"role": "user"}).json()["role"] == "user"
    assert _post(recruiter).status_code == 403


def test_admin_user_list_shows_role_points_and_subscription(world):
    _post(_make_recruiter(world, world.junior))
    users = {u["email"]: u for u in world.client("admin@example.com").get("/api/admin/users").json()}
    assert users["junior@example.com"]["role"] == "recruiter"
    assert users["junior@example.com"]["points_balance"] == 10
    assert users["admin@example.com"]["role"] == "admin" and users["admin@example.com"]["is_admin"] is True


# ------------------------------------------------------------------ manual postings

def test_publish_awards_points_logs_ledger_and_shows_on_board(world):
    recruiter = _make_recruiter(world, world.junior)
    response = _post(recruiter)
    assert response.status_code == 201
    body = response.json()
    assert body["points_awarded"] == 10 and body["balance"] == 10
    job_id = body["job"]["id"]

    wallet = recruiter.get("/api/billing/wallet").json()
    assert wallet["balance"] == 10
    assert [(t["amount"], t["action_type"], t["reference"]) for t in wallet["transactions"]] == \
        [(10, "job_posted", f"job:{job_id}")]

    # Any logged-in user sees it on the main board, flagged as a manual government posting.
    board = world.client("senior@example.com").get("/api/jobs", params={"q": "Python זוטר"}).json()
    item = next(i for i in board["items"] if i["id"] == job_id)
    assert item["is_manual"] and item["is_government_tender"]
    assert item["government_ministry"] == "משרד הבריאות" and item["tender_number"] == "2026-117"
    detail = world.client("senior@example.com").get(f"/api/jobs/{job_id}").json()
    assert detail["is_manual"] and detail["evaluation"]["scrape_run_id"] is None


def test_tender_number_is_unique_and_input_validated(world):
    recruiter = _make_recruiter(world, world.junior)
    assert _post(recruiter).status_code == 201
    duplicate = _post(recruiter, title="אחר", tender_number=" 2026-117 ")
    assert duplicate.status_code == 409 and duplicate.json()["detail"] == "duplicate_tender_number"
    assert _post(recruiter, tender_number="X", title="   ").json()["detail"] == "invalid_title"
    assert _post(recruiter, tender_number="Y", description="").json()["detail"] == "invalid_description"
    # A posting without tender details is allowed (no uniqueness clash on NULL).
    assert _post(recruiter, tender_number=None, government_ministry=None).status_code == 201
    assert _post(recruiter, tender_number=None, government_ministry=None, title="שני").status_code == 201


def test_daily_award_cap_stops_point_farming(world):
    _billing(world, max_awarded_posts_per_day=2)
    recruiter = _make_recruiter(world, world.junior)
    awards = [_post(recruiter, tender_number=f"T-{i}").json()["points_awarded"] for i in range(3)]
    assert awards == [10, 10, 0]
    assert recruiter.get("/api/billing/wallet").json()["balance"] == 20


def test_remove_reverses_award_and_blocks_spent_points(world):
    _billing(world, featured_job_points=10)
    recruiter = _make_recruiter(world, world.junior)
    first = _post(recruiter, tender_number="R-1").json()["job"]["id"]
    assert recruiter.delete(f"/api/recruiter/jobs/{first}").json() == {"points_reversed": 10}
    assert recruiter.get("/api/billing/wallet").json()["balance"] == 0
    assert world.client("senior@example.com").get(f"/api/jobs/{first}").status_code == 404

    second = _post(recruiter, tender_number="R-2").json()["job"]["id"]
    assert recruiter.post(f"/api/recruiter/jobs/{second}/feature").status_code == 200  # spends the 10
    blocked = recruiter.delete(f"/api/recruiter/jobs/{second}")
    assert blocked.status_code == 409 and blocked.json()["detail"] == "points_already_spent"
    # An admin removing it (e.g. spam) leaves the poster in debt instead.
    assert world.client("admin@example.com").delete(f"/api/recruiter/jobs/{second}").status_code == 200
    assert recruiter.get("/api/billing/wallet").json()["balance"] == -10


def test_recruiters_cannot_touch_each_others_postings(world):
    first = _make_recruiter(world, world.junior)
    job_id = _post(first).json()["job"]["id"]
    second = _make_recruiter(world, world.senior)
    assert second.delete(f"/api/recruiter/jobs/{job_id}").status_code == 404
    assert second.post(f"/api/recruiter/jobs/{job_id}/feature").status_code == 404
    assert second.get("/api/recruiter/jobs").json() == []
    assert [j["id"] for j in first.get("/api/recruiter/jobs").json()] == [job_id]
    everyone = world.client("admin@example.com").get("/api/recruiter/jobs", params={"all": "true"}).json()
    assert [j["id"] for j in everyone] == [job_id]


def test_featured_posting_is_listed_first(world):
    _billing(world, featured_job_points=10)
    recruiter = _make_recruiter(world, world.junior)
    job_id = _post(recruiter, title="משרה ממומנת").json()["job"]["id"]
    assert recruiter.post(f"/api/recruiter/jobs/{job_id}/feature").json()["featured_until"]
    first = world.client("senior@example.com").get("/api/jobs").json()["items"][0]
    assert first["id"] == job_id and first["is_featured"]
    assert recruiter.post(f"/api/recruiter/jobs/{job_id}/feature").json()["detail"] == "insufficient_points"


def test_manual_posting_survives_the_daily_refresh(world):
    job_id = _post(_make_recruiter(world, world.junior)).json()["job"]["id"]
    world.run_day("day2")  # prunes postings sites no longer list, merges new ones
    client = world.client("senior@example.com")
    assert client.get(f"/api/jobs/{job_id}").json()["is_manual"]
    assert client.get(f"/api/jobs/{job_id}/sources").json() == []  # never merged with a scraped job


# ------------------------------------------------------------------ subscriptions

def test_free_checkout_activates_subscription(world):
    client = world.client("junior@example.com")
    state = client.get("/api/billing/subscription").json()
    assert state["status"] == "inactive" and state["free_checkout"] and state["price_ils"] == 0
    active = client.post("/api/billing/subscription/checkout", json={"method": "free"}).json()
    assert active["status"] == "active" and active["current"]["amount_paid"] == 0
    assert active["current"]["payment_method"] == "free"


def test_paid_price_refuses_free_bypass(world):
    _billing(world, subscription_price_ils=29.9)
    response = world.client("junior@example.com").post("/api/billing/subscription/checkout", json={"method": "free"})
    assert response.status_code == 402 and response.json()["detail"] == "payment_required"


def test_points_redemption_pays_for_subscription(world):
    _billing(world, subscription_price_ils=29.9, subscription_price_points=20)
    recruiter = _make_recruiter(world, world.junior)
    checkout = {"method": "points"}
    assert recruiter.post("/api/billing/subscription/checkout", json=checkout).json()["detail"] == \
        "insufficient_points"
    _post(recruiter, tender_number="P-1")
    _post(recruiter, tender_number="P-2")
    state = recruiter.post("/api/billing/subscription/checkout", json=checkout).json()
    assert state["status"] == "active" and state["points_balance"] == 0
    assert state["current"]["points_spent"] == 20 and state["current"]["amount_paid"] == 0
    ledger = recruiter.get("/api/billing/wallet").json()["transactions"]
    assert ledger[0]["amount"] == -20 and ledger[0]["action_type"] == "subscription"


def test_trial_only_once(world):
    client = world.client("junior@example.com")
    assert client.post("/api/billing/subscription/trial").json()["status"] == "trial"
    again = client.post("/api/billing/subscription/trial")
    assert again.status_code == 409 and again.json()["detail"] == "trial_already_used"


def test_subscription_expires_and_renewal_stacks(session_factory, cfg):
    from backend.application.use_cases.recruiting import BillingService
    from backend.bootstrap import account_service
    from backend.domain.enums import PaymentMethod
    from backend.infrastructure.repositories.billing import SqlBillingRepository

    clock = {"now": NOW}
    with session_factory() as s:
        user = account_service(s, cfg).create_user("u@example.com", "U", "long-enough-password")
        service = BillingService(billing=SqlBillingRepository(s), cfg=BillingConfig(subscription_days=30),
                                 clock=lambda: clock["now"])
        service.checkout(user, PaymentMethod.FREE)
        renewed = service.checkout(user, PaymentMethod.FREE)  # renewing early never loses days
        assert renewed.current.expires_at == NOW + timedelta(days=30)
        clock["now"] = NOW + timedelta(days=45)
        assert service.state(user).status is SubscriptionStatus.ACTIVE  # second period
        clock["now"] = NOW + timedelta(days=61)
        assert service.state(user).status is SubscriptionStatus.INACTIVE
        assert SqlBillingRepository(s).stored_status(user.id) is SubscriptionStatus.INACTIVE


def test_billing_config_rejects_negative_prices():
    with pytest.raises(ValueError):
        BillingConfig(subscription_price_ils=-1)
    assert BillingConfig(subscription_price_ils="0", points_per_manual_job="7").points_per_manual_job == 7


# ------------------------------------------------------------------ migration

def test_migration_keeps_admins_and_round_trips(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "backend/infrastructure/db/migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    alembic_cfg.attributes["configure_logger"] = False
    command.upgrade(alembic_cfg, "0003")
    engine = create_engine(url)
    with engine.begin() as c:
        for email, admin in (("a@x.com", True), ("u@x.com", False)):
            c.execute(text("INSERT INTO users (email, display_name, is_admin, is_active, experience_level, "
                           "alerts_enabled, created_at, email_verified) VALUES (:e, 'n', :a, 1, 'junior', 1, "
                           "'2026-09-24', 1)"), {"e": email, "a": admin})
    command.upgrade(alembic_cfg, "head")
    with engine.connect() as c:
        roles = dict(c.execute(text("SELECT email, role FROM users")).all())
    assert roles == {"a@x.com": "admin", "u@x.com": "user"}
    command.downgrade(alembic_cfg, "0003")
    with engine.connect() as c:
        admins = dict(c.execute(text("SELECT email, is_admin FROM users")).all())
    assert admins == {"a@x.com": 1, "u@x.com": 0}
    engine.dispose()
