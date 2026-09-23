def test_api_requires_login(world):
    anonymous = world.client()
    assert anonymous.get("/api/jobs").status_code == 401
    assert anonymous.get("/api/stats").status_code == 401


def test_api_endpoints_over_demo_fixtures(world):
    client = world.client("junior@example.com")

    jobs = client.get("/api/jobs", params={"eligible": "true", "sort": "score"}).json()
    # Junior Backend Developer + Full Stack; QA and Help Desk are not software roles.
    assert jobs["total"] == 2 and all(j["is_eligible"] for j in jobs["items"])
    assert jobs["items"][0]["last_seen_at"].endswith("+00:00")

    job_id = next(j["id"] for j in client.get("/api/jobs").json()["items"] if j["source_count"] == 2)
    assert len(client.get(f"/api/jobs/{job_id}/sources").json()) == 2
    assert [h["change_type"] for h in client.get(f"/api/jobs/{job_id}/history").json()] == ["new", "new_source"]
    assert client.get(f"/api/jobs/{job_id}").json()["evaluation"]["is_eligible"] is True

    assert client.get(f"/api/runs/{world.run.id}").json()["scrapers"][0]["site"] == "Matrix"
    assert client.get("/api/stats").json()["new_jobs"] == 6
    assert client.get("/api/jobs/99999").status_code == 404
    assert client.get("/api/jobs", params={"page_size": 1000}).status_code == 422


def test_relevance_sort_and_role_filter(world):
    client = world.client("junior@example.com")
    items = client.get("/api/jobs").json()["items"]  # default sort = relevance
    ranks = [(i["is_junior"], i["role_type"]) for i in items]
    # Junior roles first; among juniors, software before QA / other.
    first_non_junior = next(n for n, (junior, _) in enumerate(ranks) if not junior)
    assert all(junior for junior, _ in ranks[:first_non_junior])
    assert ranks[0] == (True, "software")
    only_qa = client.get("/api/jobs", params={"role_type": "qa"}).json()["items"]
    assert only_qa and all(i["role_type"] == "qa" for i in only_qa)
