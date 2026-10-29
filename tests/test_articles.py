"""Guide articles: the body format, public reading, and the admin's create / edit / publish / delete."""
from __future__ import annotations

from backend.domain.articles import ArticleBlock
from backend.domain.services.articles import parse_article_body

NEW_ARTICLE = {
    "slug": "שאלות-לראיון", "title": "שאלות ששואלים בראיון", "summary": "מה כדאי להכין מראש.",
    "body": "## לפני הראיון\nקוראים על החברה.\n- מה היא מפתחת\n- מי הלקוחות",
    "sources": [{"name": "מקור", "url": "https://example.com/guide"}, {"name": "", "url": ""}],
    "is_published": False, "published_on": "2026-10-30",
}


def _create(admin, **changes) -> int:
    response = admin.post("/api/admin/articles", json={**NEW_ARTICLE, **changes})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_body_format_keeps_reading_order():
    assert parse_article_body("פתיח\n\n## כותרת\nפסקה\n- א\n- ב\nסיום") == (
        ArticleBlock("paragraph", "פתיח"), ArticleBlock("heading", "כותרת"), ArticleBlock("paragraph", "פסקה"),
        ArticleBlock("list", items=("א", "ב")), ArticleBlock("paragraph", "סיום"),
    )


def test_seeded_articles_are_public_and_cite_sources(world):
    visitor = world.client()
    summaries = visitor.get("/api/articles").json()
    assert len(summaries) >= 5
    for summary in summaries:
        article = visitor.get(f"/api/articles/{summary['slug']}").json()
        assert article["blocks"][0]["kind"] == "heading"
        assert article["sources"] and all(s["url"].startswith("https://") for s in article["sources"])


def test_draft_is_hidden_until_published(world):
    admin, visitor = world.client("admin@example.com"), world.client()
    article_id = _create(admin)
    slug = NEW_ARTICLE["slug"]
    assert slug not in [a["slug"] for a in visitor.get("/api/articles").json()]
    assert visitor.get(f"/api/articles/{slug}").status_code == 404
    preview = admin.get(f"/api/articles/{slug}").json()
    assert [b["kind"] for b in preview["blocks"]] == ["heading", "paragraph", "list"]
    assert preview["sources"] == [{"name": "מקור", "url": "https://example.com/guide"}]

    editable = admin.get(f"/api/admin/articles/{article_id}").json()
    assert editable["body"] == NEW_ARTICLE["body"] and editable["is_published"] is False
    assert admin.put(f"/api/admin/articles/{article_id}", json={**NEW_ARTICLE, "is_published": True}).status_code == 204
    assert visitor.get(f"/api/articles/{slug}").status_code == 200


def test_delete(world):
    admin = world.client("admin@example.com")
    article_id = _create(admin)
    assert admin.delete(f"/api/admin/articles/{article_id}").status_code == 204
    assert admin.get(f"/api/admin/articles/{article_id}").status_code == 404
    assert admin.delete(f"/api/admin/articles/{article_id}").status_code == 404


def test_validation(world):
    admin = world.client("admin@example.com")
    _create(admin)
    for changes, code in [
        ({"slug": "Bad Slug!"}, "article_bad_slug"),
        ({"title": "ab"}, "article_title_length"),
        ({"summary": "  "}, "article_summary_length"),
        ({"body": "\n \n"}, "article_body_empty"),
        ({"sources": [{"name": "מקור", "url": "not a url"}]}, "article_bad_source"),
        ({"sources": [{"name": "", "url": "https://example.com"}]}, "article_bad_source"),
    ]:
        response = admin.post("/api/admin/articles", json={**NEW_ARTICLE, "slug": "other", **changes})
        assert (response.status_code, response.json()["detail"]) == (400, code), changes
    duplicate = admin.post("/api/admin/articles", json=NEW_ARTICLE)
    assert (duplicate.status_code, duplicate.json()["detail"]) == (409, "article_slug_taken")


def test_only_the_admin_manages_articles(world):
    member, visitor = world.client("junior@example.com"), world.client()
    assert member.get("/api/admin/articles").status_code == 403
    assert member.post("/api/admin/articles", json=NEW_ARTICLE).status_code == 403
    assert visitor.post("/api/admin/articles", json=NEW_ARTICLE).status_code == 401
    assert visitor.delete("/api/admin/articles/1").status_code == 401
