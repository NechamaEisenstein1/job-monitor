"""forum: threads, posts and thanks between users (government tenders)

Revision ID: 0011
Revises: 0009
Create Date: 2026-10-16

NOTE: numbered 0011 because PR #10 adds 0010 (contact replies). Whichever of the two
merges second must point its down_revision at the other, so the history stays one line.
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forum_threads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_post_at", sa.DateTime(), nullable=False),
        sa.Column("last_post_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reply_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_forum_threads_category_last_post", "forum_threads", ["category", "last_post_at"])
    op.create_index("ix_forum_threads_last_post_at", "forum_threads", ["last_post_at"])
    op.create_index("ix_forum_threads_user_created", "forum_threads", ["user_id", "created_at"])

    op.create_table(
        "forum_posts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("thread_id", sa.Integer(), sa.ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("edited_at", sa.DateTime()),
    )
    op.create_index("ix_forum_posts_thread_created", "forum_posts", ["thread_id", "created_at"])
    op.create_index("ix_forum_posts_user_created", "forum_posts", ["user_id", "created_at"])

    op.create_table(
        "forum_thanks",
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("forum_posts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("forum_thanks")
    op.drop_index("ix_forum_posts_user_created", table_name="forum_posts")
    op.drop_index("ix_forum_posts_thread_created", table_name="forum_posts")
    op.drop_table("forum_posts")
    op.drop_index("ix_forum_threads_user_created", table_name="forum_threads")
    op.drop_index("ix_forum_threads_last_post_at", table_name="forum_threads")
    op.drop_index("ix_forum_threads_category_last_post", table_name="forum_threads")
    op.drop_table("forum_threads")
