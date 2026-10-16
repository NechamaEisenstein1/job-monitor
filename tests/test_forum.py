"""The members' forum: categories, threads, replies, edits, moderation, thanks and limits."""
from __future__ import annotations

import pytest

from backend.domain.services.forum import ForumError, clean_body, clean_title


def _thread(client, category="questions", title="איך מגישים הצעה למכרז?", body="שלום לכולם,\n\nאשמח להסבר"):
    r = client.post("/api/forum/threads", json={"category": category, "title": title, "body": body})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ------------------------------------------------------------------ text rules

def test_text_is_cleaned_and_validated():
    assert clean_title("  מכרז   משרד  הבריאות ") == "מכרז משרד הבריאות"
    assert clean_body("\n\n שורה א  \r\n\r\n\r\n\r\nשורה ב\n\n") == "שורה א\n\nשורה ב"
    for bad in ("ab", "x" * 201):
        with pytest.raises(ForumError):
            clean_title(bad)
    with pytest.raises(ForumError):
        clean_body("  \n \n")
    with pytest.raises(ForumError):
        clean_body("x" * 10_001)


# ------------------------------------------------------------------ reading and writing

def test_members_only(world):
    anon = world.client()
    assert anon.get("/api/forum/categories").status_code == 401
    assert anon.get("/api/forum/threads").status_code == 401
    assert anon.post("/api/forum/threads", json={"category": "questions", "title": "abc", "body": "x"}).status_code == 401


def test_thread_reply_and_listing(world):
    dana, yossi = world.client("junior@example.com"), world.client("senior@example.com")
    thread_id = _thread(dana)

    r = yossi.post(f"/api/forum/threads/{thread_id}/posts", json={"body": "צריך לקרוא את מסמכי המכרז"})
    assert r.status_code == 201 and r.json()["page"] == 1

    cats = {c["code"]: c for c in dana.get("/api/forum/categories").json()}
    assert list(cats) == ["questions", "sharing", "requests", "offers", "general"]
    assert cats["questions"]["thread_count"] == 1 and cats["questions"]["post_count"] == 2
    assert cats["questions"]["last_post"]["user_name"] == "יוסי"
    assert cats["sharing"]["thread_count"] == 0 and cats["sharing"]["last_post"] is None

    page = dana.get("/api/forum/threads", params={"category": "questions"}).json()
    assert page["total"] == 1
    summary = page["items"][0]
    assert summary["reply_count"] == 1 and summary["author_name"] == "דנה"
    assert summary["last_post_user_name"] == "יוסי"
    assert dana.get("/api/forum/threads", params={"category": "offers"}).json()["total"] == 0
    assert dana.get("/api/forum/threads", params={"category": "nope"}).status_code == 400

    detail = yossi.get(f"/api/forum/threads/{thread_id}").json()
    assert detail["thread"]["view_count"] == 1
    assert [p["number"] for p in detail["posts"]] == [1, 2]
    first, second = detail["posts"]
    assert first["body"] == "שלום לכולם,\n\nאשמח להסבר"
    assert first["author"]["display_name"] == "דנה" and "email" not in first["author"]
    assert first["can_edit"] is False and second["can_edit"] is True
    assert second["author"]["post_count"] == 1
    assert detail["can_reply"] is True and detail["can_moderate"] is False
    yossi.get(f"/api/forum/threads/{thread_id}", params={"count_view": "false"})  # a refresh, not a new view
    assert yossi.get(f"/api/forum/threads/{thread_id}").json()["thread"]["view_count"] == 2


def test_search_matches_titles_and_posts(world):
    dana = world.client("junior@example.com")
    a = _thread(dana, title="מכרז משרד החינוך", body="פרטים")
    b = _thread(dana, category="offers", title="מחפשת שותף", body="ניסיון במכרזי תשתיות")
    _thread(dana, title="נושא אחר", body="100% לא קשור")
    ids = lambda q: [t["id"] for t in dana.get("/api/forum/threads", params={"q": q}).json()["items"]]  # noqa: E731
    assert ids("החינוך") == [a]
    assert ids("תשתיות") == [b]
    assert ids("%") != [] and ids("_") == []  # LIKE wildcards are searched literally


def test_validation_errors(world):
    dana = world.client("junior@example.com")
    post = lambda **kw: dana.post("/api/forum/threads", json={"category": "questions", "title": "כותרת", "body": "תוכן", **kw})  # noqa: E731
    assert post(category="spam").json()["detail"] == "forum_bad_category"
    assert post(title="  א ").json()["detail"] == "forum_title_length"
    assert post(body=" \n ").json()["detail"] == "forum_body_empty"
    assert dana.post("/api/forum/threads/999/posts", json={"body": "x"}).status_code == 404
    assert dana.get("/api/forum/threads/999").status_code == 404


# ------------------------------------------------------------------ editing, deleting, moderation

def test_only_authors_and_admins_edit_and_delete(world):
    dana, yossi, admin = (world.client(e) for e in ("junior@example.com", "senior@example.com", "admin@example.com"))
    thread_id = _thread(dana)
    reply_id = yossi.post(f"/api/forum/threads/{thread_id}/posts", json={"body": "תשובה"}).json()["id"]
    first_id = dana.get(f"/api/forum/threads/{thread_id}").json()["posts"][0]["id"]

    assert dana.put(f"/api/forum/posts/{reply_id}", json={"body": "שונה"}).status_code == 403
    assert yossi.put(f"/api/forum/posts/{reply_id}", json={"body": "תשובה מעודכנת"}).status_code == 204
    assert yossi.put(f"/api/forum/threads/{thread_id}", json={"title": "כותרת חדשה"}).status_code == 403
    assert dana.put(f"/api/forum/threads/{thread_id}", json={"title": "כותרת חדשה", "category": "sharing"}).status_code == 204

    detail = dana.get(f"/api/forum/threads/{thread_id}").json()
    assert detail["thread"]["title"] == "כותרת חדשה" and detail["thread"]["category"] == "sharing"
    assert detail["posts"][1]["body"] == "תשובה מעודכנת" and detail["posts"][1]["edited_at"]

    assert dana.delete(f"/api/forum/posts/{reply_id}").status_code == 403
    assert admin.delete(f"/api/forum/posts/{reply_id}").json() == {"thread_deleted": False}
    summary = dana.get(f"/api/forum/threads/{thread_id}").json()["thread"]
    assert summary["reply_count"] == 0 and summary["last_post_user_name"] == "דנה"

    assert dana.delete(f"/api/forum/posts/{first_id}").json() == {"thread_deleted": True}
    assert dana.get(f"/api/forum/threads/{thread_id}").status_code == 404


def test_pin_and_lock_are_admin_only(world):
    dana, yossi, admin = (world.client(e) for e in ("junior@example.com", "senior@example.com", "admin@example.com"))
    old = _thread(dana, title="נושא ישן")
    new = _thread(dana, title="נושא חדש")
    assert dana.put(f"/api/forum/threads/{old}", json={"is_pinned": True}).status_code == 403

    assert admin.put(f"/api/forum/threads/{old}", json={"is_pinned": True, "is_locked": True}).status_code == 204
    assert [t["id"] for t in dana.get("/api/forum/threads").json()["items"]] == [old, new]

    # A rejected request changes nothing, even the parts that were allowed.
    bad = admin.put(f"/api/forum/threads/{new}", json={"is_locked": True, "title": "א"})
    assert bad.status_code == 400 and dana.get(f"/api/forum/threads/{new}").json()["thread"]["is_locked"] is False
    assert dana.put(f"/api/forum/threads/{new}", json={"title": "כותרת מעודכנת", "is_pinned": True}).status_code == 403
    assert dana.get(f"/api/forum/threads/{new}").json()["thread"]["title"] == "נושא חדש"

    locked = yossi.post(f"/api/forum/threads/{old}/posts", json={"body": "אפשר?"})
    assert locked.status_code == 403 and locked.json()["detail"] == "forum_locked"
    assert yossi.get(f"/api/forum/threads/{old}").json()["can_reply"] is False
    assert admin.post(f"/api/forum/threads/{old}/posts", json={"body": "הודעת מנהלת"}).status_code == 201


def test_thanks(world):
    dana, yossi = world.client("junior@example.com"), world.client("senior@example.com")
    thread_id = _thread(dana)
    post_id = dana.get(f"/api/forum/threads/{thread_id}").json()["posts"][0]["id"]

    assert dana.put(f"/api/forum/posts/{post_id}/thanks").json()["detail"] == "forum_thank_self"
    assert yossi.put(f"/api/forum/posts/{post_id}/thanks").json() == {"thanks_count": 1}
    assert yossi.put(f"/api/forum/posts/{post_id}/thanks").json() == {"thanks_count": 1}  # idempotent
    post = yossi.get(f"/api/forum/threads/{thread_id}").json()["posts"][0]
    assert post["thanks_count"] == 1 and post["thanked_by_me"] is True
    assert yossi.delete(f"/api/forum/posts/{post_id}/thanks").json() == {"thanks_count": 0}
    assert yossi.put("/api/forum/posts/999/thanks").status_code == 404


# ------------------------------------------------------------------ paging and limits

def test_replies_page_and_locate(world, monkeypatch):
    from backend.application.use_cases import forum as forum_module

    monkeypatch.setattr(forum_module, "POSTS_PAGE_SIZE", 3)
    dana = world.client("junior@example.com")
    thread_id = _thread(dana)
    pages = [dana.post(f"/api/forum/threads/{thread_id}/posts", json={"body": f"תגובה {i}"}).json()
             for i in range(4)]
    assert [p["page"] for p in pages] == [1, 1, 2, 2]
    assert dana.get(f"/api/forum/posts/{pages[3]['id']}").json() == {"thread_id": thread_id, "page": 2}

    second = dana.get(f"/api/forum/threads/{thread_id}", params={"page": 2}).json()
    assert second["total_posts"] == 5 and [p["number"] for p in second["posts"]] == [4, 5]
    assert dana.get(f"/api/forum/threads/{thread_id}", params={"page": 99}).json()["page"] == 2


def test_daily_limits(world, session_factory):
    from backend.application.use_cases.forum import ForumService
    from backend.domain.services.forum import ForumLimits
    from backend.infrastructure.repositories.forum import SqlForumRepository
    from tests.conftest import NOW

    with session_factory() as s:
        service = ForumService(SqlForumRepository(s), lambda: NOW, ForumLimits(threads_per_day=2, posts_per_day=3))
        thread_id = service.create_thread(world.junior, "general", "נושא ראשון", "א")
        service.create_thread(world.junior, "general", "נושא שני", "ב")
        with pytest.raises(ForumError) as exc:
            service.create_thread(world.junior, "general", "נושא שלישי", "ג")
        assert exc.value.code == "forum_thread_limit" and exc.value.status == 429
        service.reply(world.junior, thread_id, "תגובה")  # the two opening posts count too
        with pytest.raises(ForumError) as exc:
            service.reply(world.junior, thread_id, "עוד תגובה")
        assert exc.value.code == "forum_post_limit"
        service.reply(world.senior, thread_id, "לאחרים מותר")
        # An opening post is a message too: a new thread cannot get around the message quota.
        other = ForumService(SqlForumRepository(s), lambda: NOW, ForumLimits(threads_per_day=5, posts_per_day=1))
        with pytest.raises(ForumError) as exc:
            other.create_thread(world.senior, "general", "נושא נוסף", "ד")
        assert exc.value.code == "forum_post_limit"


def test_deleted_author_keeps_posts(world, session_factory):
    from backend.infrastructure.db.orm import UserRow

    dana, yossi = world.client("junior@example.com"), world.client("senior@example.com")
    thread_id = _thread(yossi)
    with session_factory() as s:
        s.delete(s.get(UserRow, world.senior.id))
        s.commit()
    detail = dana.get(f"/api/forum/threads/{thread_id}").json()
    assert detail["posts"][0]["author"] is None and detail["thread"]["author_name"] is None


def test_forum_pages_are_private_for_search_engines():
    from backend.api.seo import classify

    for path in ("/forum", "/forum/new", "/forum/c/questions", "/forum/t/12"):
        assert classify(path) == "private"
    assert classify("/forum/t/abc") == "unknown"
