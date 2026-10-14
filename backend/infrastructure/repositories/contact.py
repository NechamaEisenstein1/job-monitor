"""Contact messages: users write to the site admin; admins read them and mark them handled."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.application.dto import ContactMessageDto, ContactMessagePageDto
from backend.infrastructure.db.orm import ContactMessageRow, UserRow


class SqlContactRepository:
    def __init__(self, session: Session):
        self._s = session

    def add_within_limit(self, user_id: int, category: str, subject: str, body: str, now: datetime,
                         since: datetime, limit: int) -> int | None:
        """Store the message unless the user already sent `limit` since `since`; None = over the limit.
        The user's row is locked first (SELECT ... FOR UPDATE), so on PostgreSQL concurrent
        submissions by one user are counted one after another. (SQLite, used only for local
        development, ignores the lock.)"""
        try:
            self._s.execute(select(UserRow.id).where(UserRow.id == user_id).with_for_update())
            sent = self._s.scalar(select(func.count()).select_from(ContactMessageRow).where(
                ContactMessageRow.user_id == user_id, ContactMessageRow.created_at >= since)) or 0
            if sent >= limit:
                self._s.rollback()
                return None
            row = ContactMessageRow(user_id=user_id, category=category, subject=subject, body=body, created_at=now)
            self._s.add(row)
            self._s.commit()
            return row.id
        except Exception:
            self._s.rollback()
            raise

    def list(self, open_only: bool = False, page: int = 1, page_size: int = 50) -> ContactMessagePageDto:
        """Newest first, with the sender's name and email (None once the account is deleted)."""
        where = [ContactMessageRow.handled_at.is_(None)] if open_only else []
        total = self._s.scalar(select(func.count()).select_from(ContactMessageRow).where(*where)) or 0
        stmt = (select(ContactMessageRow, UserRow.display_name, UserRow.email)
                .outerjoin(UserRow, UserRow.id == ContactMessageRow.user_id).where(*where)
                .order_by(ContactMessageRow.created_at.desc(), ContactMessageRow.id.desc())
                .offset((page - 1) * page_size).limit(page_size))
        items = [ContactMessageDto(id=m.id, category=m.category, subject=m.subject, body=m.body,
                                   created_at=m.created_at, handled_at=m.handled_at,
                                   user_name=name, user_email=email)
                 for m, name, email in self._s.execute(stmt)]
        return ContactMessagePageDto(items=items, total=total, open_count=self.count_open(),
                                     page=page, page_size=page_size)

    def count_open(self) -> int:
        return self._s.scalar(select(func.count()).select_from(ContactMessageRow)
                              .where(ContactMessageRow.handled_at.is_(None))) or 0

    def set_handled(self, message_id: int, handled_at: datetime | None) -> bool:
        row = self._s.get(ContactMessageRow, message_id)
        if row is None:
            return False
        row.handled_at = handled_at
        self._s.commit()
        return True
