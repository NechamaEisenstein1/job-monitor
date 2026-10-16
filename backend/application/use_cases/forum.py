"""The forum: members ask, share, request and offer help about government tenders.
Every action needs a logged-in user; rules live in domain/services/forum.py."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from backend.application.dto import ForumCategoryDto, ForumThreadDto, ForumThreadPageDto
from backend.domain.enums import ForumCategory
from backend.domain.models import User
from backend.domain.services.forum import ForumError, ForumLimits, can_modify, can_reply, clean_body, clean_title
from backend.infrastructure.repositories.forum import PostRef, SqlForumRepository

POSTS_PAGE_SIZE = 20


def _category(code: str) -> str:
    try:
        return ForumCategory(code).value
    except ValueError as exc:
        raise ForumError("forum_bad_category") from exc


class ForumService:
    def __init__(self, repo: SqlForumRepository, clock: Callable[[], datetime], limits: ForumLimits = ForumLimits()):
        self._repo = repo
        self._now = clock
        self._limits = limits

    # ------------------------------------------------------------------ reading

    def categories(self) -> list[ForumCategoryDto]:
        return self._repo.category_stats([c.value for c in ForumCategory])

    def threads(self, category: str | None, query: str | None, page: int, page_size: int) -> ForumThreadPageDto:
        query = " ".join((query or "").split())[:100] or None
        return self._repo.list_threads(_category(category) if category else None, query, page, page_size)

    def thread(self, viewer: User, thread_id: int, page: int, *, count_view: bool = True) -> ForumThreadDto:
        if self._repo.thread_state(thread_id) is None:
            raise ForumError("not_found", 404)
        if count_view:
            self._repo.add_view(thread_id)
        summary = self._repo.thread_summary(thread_id)
        assert summary is not None
        total = self._repo.post_count(thread_id)
        last_page = max(1, -(-total // POSTS_PAGE_SIZE))
        page = min(max(1, page), last_page)
        posts = []
        for post, author_id in self._repo.thread_posts(thread_id, viewer.id, page, POSTS_PAGE_SIZE):
            post.can_edit = can_modify(viewer, author_id)
            posts.append(post)
        return ForumThreadDto(thread=summary, posts=posts, total_posts=total, page=page, page_size=POSTS_PAGE_SIZE,
                              can_reply=can_reply(viewer, locked=summary.is_locked), can_moderate=viewer.is_admin)

    # ------------------------------------------------------------------ writing

    def create_thread(self, user: User, category: str, title: str, body: str) -> int:
        category, title, body = _category(category), clean_title(title), clean_body(body)
        now = self._now()
        thread_id = self._repo.create_thread_within_limit(
            user.id, category, title, body, now, since=now - timedelta(days=1), limit=self._limits.threads_per_day)
        if thread_id is None:
            raise ForumError("forum_thread_limit", 429)
        return thread_id

    def reply(self, user: User, thread_id: int, body: str) -> tuple[int, int]:
        """Returns (post id, the page it landed on)."""
        state = self._repo.thread_state(thread_id)
        if state is None:
            raise ForumError("not_found", 404)
        if not can_reply(user, locked=state[1]):
            raise ForumError("forum_locked", 403)
        body = clean_body(body)
        now = self._now()
        post_id = self._repo.add_post_within_limit(
            thread_id, user.id, body, now, since=now - timedelta(days=1), limit=self._limits.posts_per_day)
        if post_id is None:
            raise ForumError("forum_post_limit", 429)
        return post_id, self._page_of(PostRef(post_id, thread_id, user.id, False))

    def edit_post(self, user: User, post_id: int, body: str) -> None:
        post = self._own_post(user, post_id)
        self._repo.edit_post(post.id, clean_body(body), self._now())

    def edit_thread(self, user: User, thread_id: int, *, title: str | None, category: str | None) -> None:
        state = self._repo.thread_state(thread_id)
        if state is None:
            raise ForumError("not_found", 404)
        if not can_modify(user, state[0]):
            raise ForumError("forbidden", 403)
        self._repo.edit_thread(thread_id, title=clean_title(title) if title is not None else None,
                               category=_category(category) if category is not None else None)

    def moderate(self, user: User, thread_id: int, *, is_pinned: bool | None, is_locked: bool | None) -> None:
        if not user.is_admin:
            raise ForumError("admin_only", 403)
        if self._repo.thread_state(thread_id) is None:
            raise ForumError("not_found", 404)
        self._repo.edit_thread(thread_id, is_pinned=is_pinned, is_locked=is_locked)

    def delete_post(self, user: User, post_id: int) -> bool:
        """Deleting the opening message deletes the whole thread. Returns True when it did."""
        post = self._own_post(user, post_id)
        if post.is_first:
            self._repo.delete_thread(post.thread_id)
            return True
        self._repo.delete_reply(post)
        return False

    def set_thanks(self, user: User, post_id: int, thanked: bool) -> int:
        post = self._repo.post_ref(post_id)
        if post is None:
            raise ForumError("not_found", 404)
        if post.user_id == user.id:
            raise ForumError("forum_thank_self")
        if thanked:
            self._repo.thank(post_id, user.id, self._now())
        else:
            self._repo.unthank(post_id, user.id)
        return self._repo.thanks_count(post_id)

    def locate(self, post_id: int) -> tuple[int, int]:
        """(thread id, page) of a post, for links to a specific message."""
        post = self._repo.post_ref(post_id)
        if post is None:
            raise ForumError("not_found", 404)
        return post.thread_id, self._page_of(post)

    # ------------------------------------------------------------------ helpers

    def _own_post(self, user: User, post_id: int) -> PostRef:
        post = self._repo.post_ref(post_id)
        if post is None:
            raise ForumError("not_found", 404)
        if not can_modify(user, post.user_id):
            raise ForumError("forbidden", 403)
        return post

    def _page_of(self, post: PostRef) -> int:
        return (self._repo.post_number(post) - 1) // POSTS_PAGE_SIZE + 1
