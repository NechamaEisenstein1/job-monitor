def test_api_requires_login(world):
    anonymous = world.client()
    assert anonymous.get("/api/jobs").status_code == 401
    assert anonymous.get("/api/stats").status_code == 401


def test_api_endpoints_over_demo_fixtures(world):
    client = world.client("junior@example.com")

    jobs = client.get("/api/jobs", params={"eligible": "true", "sort": "score"}).json()
    # All tech roles count: Backend, Full Stack, QA ("עד שנתיים"), Help Desk ("Entry level").
    assert jobs["total"] == 4 and all(j["is_eligible"] for j in jobs["items"])
    tech = client.get("/api/jobs", params={"role_type": "tech"}).json()
    assert tech["total"] == 6 and all(j["role_type"] != "other" for j in tech["items"])
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


def test_provider_postgres_urls_use_the_installed_driver():
    from backend.config.settings import normalize_database_url
    assert normalize_database_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_database_url("postgresql://u:p@h/db?sslmode=require") == "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert normalize_database_url("sqlite:///x.db") == "sqlite:///x.db"


def test_https_base_url_makes_cookies_secure(monkeypatch):
    from backend.config.settings import Settings
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://jobs.example.com/")
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    settings = Settings.from_env()
    assert settings.cookie_secure and settings.public_base_url == "https://jobs.example.com"


def test_security_headers_and_healthz(world):
    client = world.client()
    health = client.get("/healthz")
    assert health.status_code == 200 and health.json() == {"status": "ok"}
    for header in ("X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy"):
        assert header in health.headers
    assert client.get("/api/auth/config").headers["Cache-Control"] == "no-store"
