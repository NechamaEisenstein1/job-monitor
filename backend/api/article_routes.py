"""Guide articles: anyone reads the published ones; the admin writes, publishes and deletes them."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from backend.api.deps import AdminUser, DbSession, OptionalUser, csrf_protect
from backend.application.article_dto import ArticleDto, ArticleSummaryDto, EditableArticleDto
from backend.application.use_cases.articles import ArticleService
from backend.bootstrap import article_service
from backend.domain.articles import ArticleInput
from backend.domain.services.articles import BODY_MAX, SLUG_MAX, SOURCES_MAX, SUMMARY_MAX, TITLE_MAX, ArticleError
from backend.observability import log_event

router = APIRouter(prefix="/api", dependencies=[Depends(csrf_protect)])

ArticleId = Annotated[int, Path(ge=1)]
Slug = Annotated[str, Path(max_length=SLUG_MAX)]


def _service(session: DbSession) -> ArticleService:
    return article_service(session)


Articles = Annotated[ArticleService, Depends(_service)]


def _fail(exc: ArticleError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.code)


@router.get("/articles", response_model=list[ArticleSummaryDto])
def published_articles(articles: Articles) -> list[ArticleSummaryDto]:
    return articles.summaries(include_drafts=False)


@router.get("/articles/{slug}", response_model=ArticleDto)
def article(slug: Slug, user: OptionalUser, articles: Articles) -> ArticleDto:
    """The admin also opens drafts here, to see them exactly as they will be published."""
    try:
        return articles.article(slug, include_drafts=bool(user and user.is_admin))
    except ArticleError as exc:
        raise _fail(exc) from exc


# ------------------------------------------------------------------ admin

class ArticleSourceIn(BaseModel):
    name: str = Field(max_length=500)
    url: str = Field(max_length=2000)


class ArticleIn(BaseModel):
    """Lengths are checked exactly after trimming (domain/services/articles.py)."""
    slug: str = Field(max_length=SLUG_MAX + 100)
    title: str = Field(max_length=TITLE_MAX + 100)
    summary: str = Field(max_length=SUMMARY_MAX + 100)
    body: str = Field(max_length=BODY_MAX + 1000)
    sources: list[ArticleSourceIn] = Field(default_factory=list, max_length=SOURCES_MAX + 10)
    is_published: bool = False
    published_on: date | None = None

    def to_input(self) -> ArticleInput:
        return ArticleInput(slug=self.slug, title=self.title, summary=self.summary, body=self.body,
                            sources=[(s.name, s.url) for s in self.sources], is_published=self.is_published,
                            published_on=self.published_on)


@router.get("/admin/articles", response_model=list[ArticleSummaryDto])
def all_articles(admin: AdminUser, articles: Articles) -> list[ArticleSummaryDto]:
    return articles.summaries(include_drafts=True)


@router.get("/admin/articles/{article_id}", response_model=EditableArticleDto)
def editable_article(article_id: ArticleId, admin: AdminUser, articles: Articles) -> EditableArticleDto:
    try:
        return articles.editable(article_id)
    except ArticleError as exc:
        raise _fail(exc) from exc


@router.post("/admin/articles", status_code=201)
def create_article(body: ArticleIn, admin: AdminUser, articles: Articles) -> dict[str, int]:
    try:
        article_id = articles.create(body.to_input())
    except ArticleError as exc:
        raise _fail(exc) from exc
    log_event("article_created", article_id=article_id, admin_id=admin.id)
    return {"id": article_id}


@router.put("/admin/articles/{article_id}", status_code=204)
def update_article(article_id: ArticleId, body: ArticleIn, admin: AdminUser, articles: Articles) -> None:
    try:
        articles.update(article_id, body.to_input())
    except ArticleError as exc:
        raise _fail(exc) from exc
    log_event("article_updated", article_id=article_id, admin_id=admin.id)


@router.delete("/admin/articles/{article_id}", status_code=204)
def delete_article(article_id: ArticleId, admin: AdminUser, articles: Articles) -> None:
    try:
        articles.delete(article_id)
    except ArticleError as exc:
        raise _fail(exc) from exc
    log_event("article_deleted", article_id=article_id, admin_id=admin.id)
