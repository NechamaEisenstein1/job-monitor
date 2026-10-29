"""Article persistence."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.domain.articles import Article, ArticleDraft, ArticleSource
from backend.infrastructure.db.orm import ArticleRow


class SlugTaken(Exception):
    """Another article already uses this address."""


def _to_article(row: ArticleRow) -> Article:
    return Article(
        id=row.id, slug=row.slug, title=row.title, summary=row.summary, body=row.body,
        sources=tuple(ArticleSource(**source) for source in row.sources), is_published=row.is_published,
        published_on=row.published_on, updated_at=row.updated_at,
    )


def _draft_columns(draft: ArticleDraft) -> dict:
    return {**asdict(draft), "sources": [asdict(source) for source in draft.sources]}


class SqlArticleRepository:
    def __init__(self, session: Session):
        self._s = session

    def list(self, *, published_only: bool) -> list[Article]:
        """Newest first."""
        query = select(ArticleRow).order_by(ArticleRow.published_on.desc(), ArticleRow.id.desc())
        if published_only:
            query = query.where(ArticleRow.is_published.is_(True))
        return [_to_article(row) for row in self._s.scalars(query)]

    def by_id(self, article_id: int) -> Article | None:
        row = self._s.get(ArticleRow, article_id)
        return _to_article(row) if row else None

    def by_slug(self, slug: str) -> Article | None:
        row = self._s.scalar(select(ArticleRow).where(ArticleRow.slug == slug))
        return _to_article(row) if row else None

    def create(self, draft: ArticleDraft, now: datetime) -> int:
        row = ArticleRow(**_draft_columns(draft), created_at=now, updated_at=now)
        self._s.add(row)
        self._commit()
        return row.id

    def update(self, article_id: int, draft: ArticleDraft, now: datetime) -> bool:
        row = self._s.get(ArticleRow, article_id)
        if row is None:
            return False
        for column, value in _draft_columns(draft).items():
            setattr(row, column, value)
        row.updated_at = now
        self._commit()
        return True

    def delete(self, article_id: int) -> bool:
        deleted = self._s.execute(delete(ArticleRow).where(ArticleRow.id == article_id)).rowcount
        self._s.commit()
        return bool(deleted)

    def _commit(self) -> None:
        try:
            self._s.commit()
        except IntegrityError as exc:
            self._s.rollback()
            raise SlugTaken from exc
