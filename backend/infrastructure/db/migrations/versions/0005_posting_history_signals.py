"""posting history (ghost / new / multi-agency labels) + fake-junior facets

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("job_evaluations") as batch:
        batch.add_column(sa.Column("required_years", sa.Float()))
        batch.add_column(sa.Column("junior_title_mismatch", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "posting_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recruitment_company", sa.String(200), nullable=False),
        sa.Column("posting_key", sa.String(260), nullable=False),
        sa.Column("title_key", sa.String(300), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("origin_first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("gone_at", sa.DateTime()),
        sa.Column("reposts", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("recruitment_company", "posting_key", name="uq_posting_history_company_key"),
    )
    op.create_index("ix_posting_history_company_title", "posting_history", ["recruitment_company", "title_key"])

    # Seed from the postings we already track (history starts at their first sighting).
    # title_key is filled in Python so it uses the same normalization as the pipeline.
    from backend.domain.services.signals import posting_key, title_key

    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT recruitment_company, source_job_id, source_url_fingerprint, external_title, first_seen_at, "
        "last_seen_at FROM job_sources")).all()
    table = sa.table("posting_history", *(sa.column(c) for c in (
        "recruitment_company", "posting_key", "title_key", "first_seen_at", "origin_first_seen_at", "last_seen_at")))
    seen = set()
    batch = []
    for company, source_id, fingerprint, title, first, last in rows:
        key = posting_key(source_id, fingerprint)
        if (company, key) in seen:
            continue
        seen.add((company, key))
        batch.append({"recruitment_company": company, "posting_key": key, "title_key": title_key(title),
                      "first_seen_at": first, "origin_first_seen_at": first, "last_seen_at": last})
    for start in range(0, len(batch), 1000):
        op.bulk_insert(table, batch[start:start + 1000])


def downgrade() -> None:
    op.drop_index("ix_posting_history_company_title", table_name="posting_history")
    op.drop_table("posting_history")
    with op.batch_alter_table("job_evaluations") as batch:
        batch.drop_column("junior_title_mismatch")
        batch.drop_column("required_years")
