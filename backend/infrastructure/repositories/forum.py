"""Forum persistence: threads, posts (the first post of a thread is its opening message), thanks.
Thread counters (reply_count, last_post_*) are maintained here on every write."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from backend.application.dto import (
    ForumAuthorDto, ForumCategoryDto, ForumLastPostDto, ForumPostDto, ForumThreadPageDto, ForumThreadSummaryDto,
)
from backend.infrastructure.db.orm import ForumPostRow, ForumSubmissionRow, ForumThanksRow, ForumThreadRow, UserRow


class QuotaExceeded(Exception):
    """The user reached a daily limit; `kind` is "threads" or "posts"."""

    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


@dataclass(frozen=True)
class PostRef:
    id: int
    thread_id: int
    user_id: int | None
    is_first: bool


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlForumRepository:
    def __init__(self, session: Session):
        self._s = session

    # ------------------------------------------------------------------ reads

    def category_stats(self, codes: list[str]) -> list[ForumCategoryDto]:
        """Every category in `codes` order, empty ones included, with its latest activity."""
        threads = dict(self._s.execute(
            select(ForumThreadRow.category, func.count()).group_by(ForumThreadRow.category)).all())
        posts = dict(self._s.execute(
            select(ForumThreadRow.category, func.count(ForumPostRow.id))
            .join(ForumPostRow, ForumPostRow.thread_id == ForumThreadRow.id)
            .group_by(ForumThreadRow.category)).all())
        latest = (select(ForumThreadRow.category, func.max(ForumThreadRow.last_post_at).label("at"))
                  .group_by(ForumThreadRow.category).subquery())
        last_by_cat: dict[str, ForumLastPostDto] = {}
        rows = self._s.execute(
            select(ForumThreadRow, UserRow.display_name)
            .join(latest, (latest.c.category == ForumThreadRow.category) & (latest.c.at == ForumThreadRow.last_post_at))
            .outerjoin(UserRow, UserRow.id == ForumThreadRow.last_post_user_id)
            .order_by(ForumThreadRow.id.desc()))
        for t, name in rows:
            last_by_cat.setdefault(t.category, ForumLastPostDto(
                thread_id=t.id, thread_title=t.title, at=t.last_post_at, user_name=name))
        return [ForumCategoryDto(code=c, thread_count=threads.get(c, 0), post_count=posts.get(c, 0),
                                 last_post=last_by_cat.get(c)) for c in codes]

    def _summary_query(self):
        author, last = aliased(UserRow), aliased(UserRow)
        return (select(ForumThreadRow, author.display_name, last.display_name)
                .outerjoin(author, author.id == ForumThreadRow.user_id)
                .outerjoin(last, last.id == ForumThreadRow.last_post_user_id))

    @staticmethod
    def _summary(t: ForumThreadRow, author_name: str | None, last_name: str | None) -> ForumThreadSummaryDto:
        return ForumThreadSummaryDto(
            id=t.id, category=t.category, title=t.title, author_id=t.user_id, author_name=author_name,
            created_at=t.created_at, last_post_at=t.last_post_at, last_post_user_name=last_name,
            reply_count=t.reply_count, view_count=t.view_count, is_pinned=t.is_pinned, is_locked=t.is_locked)

    def list_threads(self, category: str | None, query: str | None, page: int, page_size: int) -> ForumThreadPageDto:
        """Pinned threads first, then by latest activity. `query` matches the title or any post."""
        where = []
        if category:
            where.append(ForumThreadRow.category == category)
        if query:
            pattern = f"%{_escape_like(query)}%"
            where.append(or_(
                ForumThreadRow.title.ilike(pattern, escape="\\"),
                exists().where(ForumPostRow.thread_id == ForumThreadRow.id,
                               ForumPostRow.body.ilike(pattern, escape="\\")),
            ))
        total = self._s.scalar(select(func.count()).select_from(ForumThreadRow).where(*where)) or 0
        rows = self._s.execute(
            self._summary_query().where(*where)
            .order_by(ForumThreadRow.is_pinned.desc(), ForumThreadRow.last_post_at.desc(), ForumThreadRow.id.desc())
            .offset((page - 1) * page_size).limit(page_size))
        return ForumThreadPageDto(items=[self._summary(*r) for r in rows], total=total, page=page, page_size=page_size)

    def thread_summary(self, thread_id: int) -> ForumThreadSummaryDto | None:
        row = self._s.execute(self._summary_query().where(ForumThreadRow.id == thread_id)).first()
        return self._summary(*row) if row else None

    def thread_posts(self, thread_id: int, viewer_id: int, page: int, page_size: int) -> list[tuple[ForumPostDto, int | None]]:
        """The page's posts, oldest first, numbered from 1 across the whole thread. Each comes with
        its author id so the caller can decide `can_edit`."""
        offset = (page - 1) * page_size
        rows = self._s.execute(
            select(ForumPostRow, UserRow)
            .outerjoin(UserRow, UserRow.id == ForumPostRow.user_id)
            .where(ForumPostRow.thread_id == thread_id)
            .order_by(ForumPostRow.created_at, ForumPostRow.id)
            .offset(offset).limit(page_size)).all()
        post_ids = [p.id for p, _ in rows]
        user_ids = {p.user_id for p, _ in rows if p.user_id is not None}
        thanks = dict(self._s.execute(
            select(ForumThanksRow.post_id, func.count()).where(ForumThanksRow.post_id.in_(post_ids))
            .group_by(ForumThanksRow.post_id)).all()) if post_ids else {}
        mine = set(self._s.scalars(
            select(ForumThanksRow.post_id).where(ForumThanksRow.post_id.in_(post_ids),
                                                 ForumThanksRow.user_id == viewer_id))) if post_ids else set()
        counts = dict(self._s.execute(
            select(ForumPostRow.user_id, func.count()).where(ForumPostRow.user_id.in_(user_ids))
            .group_by(ForumPostRow.user_id)).all()) if user_ids else {}
        out = []
        for i, (p, u) in enumerate(rows):
            author = ForumAuthorDto(id=u.id, display_name=u.display_name, role=u.role, joined_at=u.created_at,
                                    post_count=counts.get(u.id, 0)) if u else None
            out.append((ForumPostDto(id=p.id, number=offset + i + 1, body=p.body, created_at=p.created_at,
                                     edited_at=p.edited_at, author=author, thanks_count=thanks.get(p.id, 0),
                                     thanked_by_me=p.id in mine, can_edit=False), p.user_id))
        return out

    def post_count(self, thread_id: int) -> int:
        return self._s.scalar(select(func.count()).select_from(ForumPostRow)
                              .where(ForumPostRow.thread_id == thread_id)) or 0

    def post_ref(self, post_id: int) -> PostRef | None:
        post = self._s.get(ForumPostRow, post_id)
        if post is None:
            return None
        first_id = self._s.scalar(select(ForumPostRow.id).where(ForumPostRow.thread_id == post.thread_id)
                                  .order_by(ForumPostRow.created_at, ForumPostRow.id).limit(1))
        return PostRef(id=post.id, thread_id=post.thread_id, user_id=post.user_id, is_first=first_id == post.id)

    def post_number(self, post: PostRef) -> int:
        """1-based position of the post in its thread (to open the right page)."""
        created = self._s.scalar(select(ForumPostRow.created_at).where(ForumPostRow.id == post.id))
        return (self._s.scalar(select(func.count()).select_from(ForumPostRow).where(
            ForumPostRow.thread_id == post.thread_id,
            or_(ForumPostRow.created_at < created, (ForumPostRow.created_at == created) & (ForumPostRow.id <= post.id)),
        )) or 0)

    def thread_state(self, thread_id: int) -> tuple[int | None, bool] | None:
        """(author id, is_locked), or None when the thread does not exist."""
        row = self._s.execute(select(ForumThreadRow.user_id, ForumThreadRow.is_locked)
                              .where(ForumThreadRow.id == thread_id)).first()
        return (row[0], row[1]) if row else None

    # ------------------------------------------------------------------ writes

    def _check_quota(self, user_id: int, since: datetime, *, thread_limit: int | None, post_limit: int) -> None:
        """Locks the user's row first (SELECT ... FOR UPDATE) so on PostgreSQL concurrent
        submissions by one user are counted one after another (SQLite ignores the lock).
        Raises QuotaExceeded("threads" | "posts")."""
        self._s.execute(select(UserRow.id).where(UserRow.id == user_id).with_for_update())
        # Counted from the submissions log, not from forum_posts: deleting a message does not
        # give back its place in the quota.
        used = dict(self._s.execute(
            select(ForumSubmissionRow.kind, func.count()).where(
                ForumSubmissionRow.user_id == user_id, ForumSubmissionRow.created_at >= since)
            .group_by(ForumSubmissionRow.kind)).all())
        if thread_limit is not None and used.get("thread", 0) >= thread_limit:
            raise QuotaExceeded("threads")
        if used.get("post", 0) >= post_limit:
            raise QuotaExceeded("posts")

    def _log_submission(self, user_id: int, now: datetime, *kinds: str) -> None:
        self._s.add_all(ForumSubmissionRow(user_id=user_id, kind=k, created_at=now) for k in kinds)

    def _lock_thread(self, thread_id: int) -> None:
        """Replies to one thread are added and removed one after another (PostgreSQL row lock),
        so the counters below are always recomputed from committed posts."""
        self._s.execute(select(ForumThreadRow.id).where(ForumThreadRow.id == thread_id).with_for_update())

    def _refresh_counters(self, thread_id: int) -> None:
        """reply_count and last_post_* straight from the posts, never incremented blindly."""
        last = self._s.execute(
            select(ForumPostRow.created_at, ForumPostRow.user_id).where(ForumPostRow.thread_id == thread_id)
            .order_by(ForumPostRow.created_at.desc(), ForumPostRow.id.desc()).limit(1)).first()
        if last is None:
            return
        self._s.execute(update(ForumThreadRow).where(ForumThreadRow.id == thread_id).values(
            reply_count=max(0, self.post_count(thread_id) - 1), last_post_at=last[0], last_post_user_id=last[1]))

    def create_thread_within_limit(self, user_id: int, category: str, title: str, body: str, now: datetime,
                                   since: datetime, thread_limit: int, post_limit: int) -> int:
        """The thread and its opening post in one transaction. The opening post counts
        towards the message quota too."""
        try:
            self._check_quota(user_id, since, thread_limit=thread_limit, post_limit=post_limit)
            thread = ForumThreadRow(category=category, user_id=user_id, title=title, created_at=now,
                                    last_post_at=now, last_post_user_id=user_id, reply_count=0, view_count=0,
                                    is_pinned=False, is_locked=False)
            self._s.add(thread)
            self._s.flush()
            self._s.add(ForumPostRow(thread_id=thread.id, user_id=user_id, body=body, created_at=now))
            self._log_submission(user_id, now, "thread", "post")
            self._s.commit()
            return thread.id
        except Exception:
            self._s.rollback()
            raise

    def add_post_within_limit(self, thread_id: int, user_id: int, body: str, now: datetime,
                              since: datetime, limit: int) -> int:
        """Lock order: the user's row, then the thread's (delete_reply takes only the thread's)."""
        try:
            self._check_quota(user_id, since, thread_limit=None, post_limit=limit)
            self._lock_thread(thread_id)
            post = ForumPostRow(thread_id=thread_id, user_id=user_id, body=body, created_at=now)
            self._s.add(post)
            self._log_submission(user_id, now, "post")
            self._s.flush()
            self._refresh_counters(thread_id)
            self._s.commit()
            return post.id
        except Exception:
            self._s.rollback()
            raise

    def edit_post(self, post_id: int, body: str, now: datetime) -> None:
        self._s.execute(update(ForumPostRow).where(ForumPostRow.id == post_id).values(body=body, edited_at=now))
        self._s.commit()

    def edit_thread(self, thread_id: int, *, title: str | None = None, category: str | None = None,
                    is_pinned: bool | None = None, is_locked: bool | None = None) -> None:
        values = {k: v for k, v in dict(title=title, category=category, is_pinned=is_pinned,
                                        is_locked=is_locked).items() if v is not None}
        if values:
            self._s.execute(update(ForumThreadRow).where(ForumThreadRow.id == thread_id).values(**values))
            self._s.commit()

    def delete_thread(self, thread_id: int) -> None:
        self._s.execute(delete(ForumThreadRow).where(ForumThreadRow.id == thread_id))
        self._s.commit()

    def delete_reply(self, post: PostRef) -> None:
        """Removes a reply and recomputes the thread's counters from what is left."""
        try:
            self._lock_thread(post.thread_id)
            self._s.execute(delete(ForumPostRow).where(ForumPostRow.id == post.id))
            self._refresh_counters(post.thread_id)
            self._s.commit()
        except Exception:
            self._s.rollback()
            raise

    def add_view(self, thread_id: int) -> None:
        self._s.execute(update(ForumThreadRow).where(ForumThreadRow.id == thread_id)
                        .values(view_count=ForumThreadRow.view_count + 1))
        self._s.commit()

    def thank(self, post_id: int, user_id: int, now: datetime) -> None:
        """Idempotent: thanking twice keeps one row."""
        try:
            self._s.add(ForumThanksRow(post_id=post_id, user_id=user_id, created_at=now))
            self._s.commit()
        except IntegrityError:
            self._s.rollback()

    def unthank(self, post_id: int, user_id: int) -> None:
        self._s.execute(delete(ForumThanksRow).where(ForumThanksRow.post_id == post_id,
                                                     ForumThanksRow.user_id == user_id))
        self._s.commit()

    def thanks_count(self, post_id: int) -> int:
        return self._s.scalar(select(func.count()).select_from(ForumThanksRow)
                              .where(ForumThanksRow.post_id == post_id)) or 0
