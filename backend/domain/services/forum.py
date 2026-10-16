"""Forum rules: who may write, edit, delete and moderate, and how text is cleaned.
Pure functions - no persistence here."""
from __future__ import annotations

from dataclasses import dataclass

from backend.domain.models import User

TITLE_MIN, TITLE_MAX = 3, 200
BODY_MAX = 10_000


class ForumError(Exception):
    """User-facing failure. `code` is stable for the UI to translate; `status` is the HTTP status."""

    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class ForumLimits:
    threads_per_day: int = 10
    posts_per_day: int = 100


def clean_title(value: str) -> str:
    """Collapses whitespace; a title is one line."""
    title = " ".join(value.split())
    if not TITLE_MIN <= len(title) <= TITLE_MAX:
        raise ForumError("forum_title_length")
    return title


def clean_body(value: str) -> str:
    """Keeps line breaks (paragraphs, lists) but drops trailing spaces and runs of blank lines."""
    lines = [line.rstrip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    out: list[str] = []
    for line in lines:
        if not line and (not out or not out[-1]):
            continue  # no leading blank lines, at most one blank line in a row
        out.append(line)
    body = "\n".join(out).strip()
    if not body:
        raise ForumError("forum_body_empty")
    if len(body) > BODY_MAX:
        raise ForumError("forum_body_too_long")
    return body


def can_modify(user: User, author_id: int | None) -> bool:
    """Authors edit and delete their own posts; admins moderate everything."""
    return user.is_admin or (author_id is not None and author_id == user.id)


def can_reply(user: User, *, locked: bool) -> bool:
    """A locked thread is read-only for everyone but admins."""
    return user.is_admin or not locked
