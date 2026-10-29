"""Guide articles: anyone reads the published ones, the admin writes, publishes and deletes.
Rules and the body format live in domain/services/articles.py."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime

from backend.application.article_dto import ArticleDto, ArticleSummaryDto, EditableArticleDto
from backend.domain.articles import Article, ArticleInput
from backend.domain.services.articles import ArticleError, clean_article, parse_article_body, reading_minutes
from backend.infrastructure.repositories.articles import SlugTaken, SqlArticleRepository


def _summary_fields(article: Article) -> dict:
    return {**asdict(article), "reading_minutes": reading_minutes(article.body)}


class ArticleService:
    def __init__(self, repo: SqlArticleRepository, clock: Callable[[], datetime]):
        self._repo = repo
        self._now = clock

    # ------------------------------------------------------------------ reading

    def published(self) -> list[Article]:
        return self._repo.list(published_only=True)

    def published_by_slug(self, slug: str) -> Article | None:
        article = self._repo.by_slug(slug)
        return article if article and article.is_published else None

    def summaries(self, *, include_drafts: bool) -> list[ArticleSummaryDto]:
        return [ArticleSummaryDto(**_summary_fields(a)) for a in self._repo.list(published_only=not include_drafts)]

    def article(self, slug: str, *, include_drafts: bool) -> ArticleDto:
        article = self._repo.by_slug(slug) if include_drafts else self.published_by_slug(slug)
        if article is None:
            raise ArticleError("not_found", 404)
        blocks = [asdict(block) for block in parse_article_body(article.body)]
        return ArticleDto(**{**_summary_fields(article), "blocks": blocks})

    def editable(self, article_id: int) -> EditableArticleDto:
        article = self._repo.by_id(article_id)
        if article is None:
            raise ArticleError("not_found", 404)
        return EditableArticleDto(**_summary_fields(article))

    # ------------------------------------------------------------------ writing (admin)

    def create(self, raw: ArticleInput) -> int:
        draft = clean_article(raw, self._now().date())
        try:
            return self._repo.create(draft, self._now())
        except SlugTaken as exc:
            raise ArticleError("article_slug_taken", 409) from exc

    def update(self, article_id: int, raw: ArticleInput) -> None:
        draft = clean_article(raw, self._now().date())
        try:
            updated = self._repo.update(article_id, draft, self._now())
        except SlugTaken as exc:
            raise ArticleError("article_slug_taken", 409) from exc
        if not updated:
            raise ArticleError("not_found", 404)

    def delete(self, article_id: int) -> None:
        if not self._repo.delete(article_id):
            raise ArticleError("not_found", 404)
