"""Shared salary offers: sharing, the admin's review, comparing a level, and keeping members anonymous."""
from __future__ import annotations

from datetime import date

from backend.domain.services.salary_offer_rules import months_before

THIS_MONTH = date.today().replace(day=1).isoformat()

OFFER = {
    "level": "a", "role_type": "devops", "agency": "Yael", "client_type": "government",
    "offered_month": THIS_MONTH, "outcome": "accepted", "base_salary": 9200,
    "extras": [{"kind": "travel", "amount": 350, "included_in_total": True},
               {"kind": "refreshments", "amount": 50, "included_in_total": True},
               {"kind": "phone", "amount": 100, "included_in_total": True}],
    "hours_per_day": 8.9, "vacation_days": 17, "sick_pay": "full_from_day_two",
    "contribution_base": "base_salary", "contribution_percent": 100, "study_fund_start": "not_stated",
    "details": {"holiday_eve_hours": 4.5, "chol_hamoed_hours": 6, "laptop": True, "initial_base_salary": 9000},
    "received_personally": True,
}


def _share(client, **changes) -> int:
    response = client.post("/api/salary-offers", json={**OFFER, **changes})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _share_approved(world, count: int, **changes) -> list[int]:
    member, admin = world.client("junior@example.com"), world.client("admin@example.com")
    ids = [_share(member, **changes) for _ in range(count)]
    for offer_id in ids:
        assert admin.post(f"/api/admin/salary-offers/{offer_id}/approve").status_code == 204
    return ids


def test_offer_counts_only_after_the_admin_approves_it(world):
    member, admin = world.client("junior@example.com"), world.client("admin@example.com")
    offer_id = _share(member)
    assert member.get("/api/salary-offers", params={"level": "a"}).json() == []
    assert [o["id"] for o in admin.get("/api/admin/salary-offers").json()] == [offer_id]
    assert member.get("/api/salary-offers/mine").json()[0]["status"] == "pending"

    assert admin.post(f"/api/admin/salary-offers/{offer_id}/approve").status_code == 204
    assert admin.post(f"/api/admin/salary-offers/{offer_id}/approve").status_code == 404
    offer = world.client("senior@example.com").get("/api/salary-offers", params={"level": "a"}).json()[0]
    assert offer["total_salary"] == 9700 and offer["negotiation_gain"] > 0
    assert offer["details"]["laptop"] is True
    assert "submitted_by" not in offer and "status" not in offer


def test_rejected_offer_stays_out(world):
    member, admin = world.client("junior@example.com"), world.client("admin@example.com")
    offer_id = _share(member)
    assert admin.post(f"/api/admin/salary-offers/{offer_id}/reject").status_code == 204
    assert member.get("/api/salary-offers", params={"level": "a"}).json() == []


def test_summary_hides_figures_resting_on_too_few_offers(world):
    _share_approved(world, 2)
    summary = world.client("senior@example.com").get("/api/salary-offers/summary", params={"level": "a"}).json()
    assert summary["offer_count"] == 2
    assert summary["total_salary"] is None and summary["sick_pay_above_law_share"] is None
    assert summary["agencies"] == [{"agency": "Yael", "offer_count": 2, "total_salary": None}]

    _share_approved(world, 1, base_salary=10200)
    summary = world.client("senior@example.com").get("/api/salary-offers/summary", params={"level": "a"}).json()
    assert summary["total_salary"]["median"] == 9700
    assert summary["sick_pay_above_law_share"] == 1
    assert summary["agencies"][0]["total_salary"]["high_quartile"] == 10200


def test_filters_by_client_type_and_period(world):
    old_month = months_before(date.today(), 18).isoformat()
    _share_approved(world, 1, client_type="private")
    _share_approved(world, 1, offered_month=old_month)
    viewer = world.client("senior@example.com")
    assert len(viewer.get("/api/salary-offers", params={"level": "a", "client_type": "private"}).json()) == 1
    assert len(viewer.get("/api/salary-offers", params={"level": "a"}).json()) == 1
    assert len(viewer.get("/api/salary-offers", params={"level": "a", "months_back": 24}).json()) == 2
    assert viewer.get("/api/salary-offers", params={"level": "b"}).json() == []


def test_member_withdraws_only_her_own_offer(world):
    offer_id = _share(world.client("junior@example.com"))
    assert world.client("senior@example.com").delete(f"/api/salary-offers/{offer_id}").status_code == 404
    assert world.client("junior@example.com").delete(f"/api/salary-offers/{offer_id}").status_code == 204
    assert world.client("admin@example.com").get("/api/admin/salary-offers").json() == []


def test_validation(world):
    member = world.client("junior@example.com")
    for changes, code in [
        ({"received_personally": False}, "salary_offer_not_first_hand"),
        ({"role_type": "astronaut"}, "salary_offer_bad_role"),
        ({"agency": "   "}, "salary_offer_bad_agency"),
        ({"offered_month": "2000-01-01"}, "salary_offer_bad_month"),
        ({"base_salary": 0}, "salary_offer_bad_salary"),
        ({"hours_per_day": 20}, "salary_offer_bad_hours"),
        ({"details": {"unknown_term": 1}}, "salary_offer_bad_detail"),
        ({"details": {"holiday_eve_hours": 30}}, "salary_offer_bad_detail"),
    ]:
        response = member.post("/api/salary-offers", json={**OFFER, **changes})
        assert (response.status_code, response.json()["detail"]) == (400, code), changes


def test_only_members_and_admins_reach_the_offers(world):
    assert world.client().get("/api/salary-offers", params={"level": "a"}).status_code == 401
    assert world.client("junior@example.com").get("/api/admin/salary-offers").status_code == 403
    options = world.client("junior@example.com").get("/api/salary-offers/options").json()
    assert "devops" in options["role_types"] and options["agencies"]
