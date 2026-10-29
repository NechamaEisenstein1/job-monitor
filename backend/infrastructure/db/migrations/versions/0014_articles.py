"""guide articles, managed by the admin; starts with the articles in seed/articles.json

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-30
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

SEED_FILE = Path(__file__).resolve().parents[1] / "seed" / "articles.json"


def upgrade() -> None:
    articles = op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.String(400), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_articles_published", "articles", ["is_published", "published_on"])

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    op.bulk_insert(articles, [
        {**article, "published_on": date.fromisoformat(article["published_on"]), "is_published": True,
         "created_at": now, "updated_at": now}
        for article in seed
    ])


def downgrade() -> None:
    op.drop_index("ix_articles_published", table_name="articles")
    op.drop_table("articles")
