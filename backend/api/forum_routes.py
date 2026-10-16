"""The members' forum about government tenders. Logged-in users only, for reading and writing."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from backend.api.deps import CurrentUser, DbSession, csrf_protect
from backend.application.dto import ForumCategoryDto, ForumThreadDto, ForumThreadPageDto
from backend.application.use_cases.forum import ForumService
from backend.bootstrap import forum_service
from backend.domain.services.forum import BODY_MAX, TITLE_MAX, ForumError
from backend.observability import log_event

router = APIRouter(prefix="/api/forum", dependencies=[Depends(csrf_protect)])

ThreadId = Annotated[int, Path(ge=1)]
PostId = Annotated[int, Path(ge=1)]


def _service(session: DbSession) -> ForumService:
    return forum_service(session)


Forum = Annotated[ForumService, Depends(_service)]


def _fail(exc: ForumError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.code)


@router.get("/categories", response_model=list[ForumCategoryDto])
def categories(user: CurrentUser, forum: Forum) -> list[ForumCategoryDto]:
    return forum.categories()


@router.get("/threads", response_model=ForumThreadPageDto)
def threads(user: CurrentUser, forum: Forum,
            category: Annotated[str | None, Query(max_length=16)] = None,
            q: Annotated[str | None, Query(max_length=200)] = None,
            page: Annotated[int, Query(ge=1, le=10_000)] = 1,
            page_size: Annotated[int, Query(ge=1, le=50)] = 25) -> ForumThreadPageDto:
    try:
        return forum.threads(category, q, page, page_size)
    except ForumError as exc:
        raise _fail(exc) from exc


class ThreadIn(BaseModel):
    category: str = Field(max_length=16)
    title: str = Field(max_length=TITLE_MAX + 100)
    body: str = Field(max_length=BODY_MAX + 1000)  # the exact limit is checked after trimming


@router.post("/threads", status_code=201)
def create_thread(body: ThreadIn, user: CurrentUser, forum: Forum) -> dict[str, int]:
    try:
        thread_id = forum.create_thread(user, body.category, body.title, body.body)
    except ForumError as exc:
        raise _fail(exc) from exc
    log_event("forum_thread", thread_id=thread_id, user_id=user.id, category=body.category)
    return {"id": thread_id}


@router.get("/threads/{thread_id}", response_model=ForumThreadDto)
def thread(thread_id: ThreadId, user: CurrentUser, forum: Forum,
           page: Annotated[int, Query(ge=1, le=10_000)] = 1, count_view: bool = True) -> ForumThreadDto:
    """`count_view=false` when the page only refreshes after the viewer's own action."""
    try:
        return forum.thread(user, thread_id, page, count_view=count_view)
    except ForumError as exc:
        raise _fail(exc) from exc


class ThreadUpdateIn(BaseModel):
    title: str | None = Field(default=None, max_length=TITLE_MAX + 100)
    category: str | None = Field(default=None, max_length=16)
    is_pinned: bool | None = None   # admins only
    is_locked: bool | None = None   # admins only


@router.put("/threads/{thread_id}", status_code=204)
def update_thread(thread_id: ThreadId, body: ThreadUpdateIn, user: CurrentUser, forum: Forum) -> None:
    try:
        forum.update_thread(user, thread_id, title=body.title, category=body.category,
                            is_pinned=body.is_pinned, is_locked=body.is_locked)
    except ForumError as exc:
        raise _fail(exc) from exc


class PostIn(BaseModel):
    body: str = Field(max_length=BODY_MAX + 1000)


@router.post("/threads/{thread_id}/posts", status_code=201)
def reply(thread_id: ThreadId, body: PostIn, user: CurrentUser, forum: Forum) -> dict[str, int]:
    try:
        post_id, page = forum.reply(user, thread_id, body.body)
    except ForumError as exc:
        raise _fail(exc) from exc
    return {"id": post_id, "page": page}


@router.get("/posts/{post_id}")
def locate_post(post_id: PostId, user: CurrentUser, forum: Forum) -> dict[str, int]:
    try:
        thread_id, page = forum.locate(post_id)
    except ForumError as exc:
        raise _fail(exc) from exc
    return {"thread_id": thread_id, "page": page}


@router.put("/posts/{post_id}", status_code=204)
def edit_post(post_id: PostId, body: PostIn, user: CurrentUser, forum: Forum) -> None:
    try:
        forum.edit_post(user, post_id, body.body)
    except ForumError as exc:
        raise _fail(exc) from exc


@router.delete("/posts/{post_id}")
def delete_post(post_id: PostId, user: CurrentUser, forum: Forum) -> dict[str, bool]:
    try:
        thread_deleted = forum.delete_post(user, post_id)
    except ForumError as exc:
        raise _fail(exc) from exc
    log_event("forum_post_deleted", post_id=post_id, user_id=user.id, thread_deleted=thread_deleted)
    return {"thread_deleted": thread_deleted}


@router.put("/posts/{post_id}/thanks")
def thank(post_id: PostId, user: CurrentUser, forum: Forum) -> dict[str, int]:
    try:
        return {"thanks_count": forum.set_thanks(user, post_id, True)}
    except ForumError as exc:
        raise _fail(exc) from exc


@router.delete("/posts/{post_id}/thanks")
def unthank(post_id: PostId, user: CurrentUser, forum: Forum) -> dict[str, int]:
    try:
        return {"thanks_count": forum.set_thanks(user, post_id, False)}
    except ForumError as exc:
        raise _fail(exc) from exc
