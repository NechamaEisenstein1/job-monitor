"""Contact messages: users write to the site admin; admins read them and mark them handled."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.application.dto import ContactMessageDto
from backend.infrastructure.db.orm import ContactMessageRow, UserRow


class SqlContactRepository:
    def __init__(self, session: Session):
        self._s = session

    def add(self, user_id: int, category: str, subject: str, body: str, now: datetime) -> int:
        row = ContactMessageRow(user_id=user_id, category=category, subject=subject, body=body, created_at=now)
        self._s.add(row)
        self._s.commit()
        return row.id

    def count_by_user_since(self, user_id: int, since: datetime) -> int:
        return self._s.scalar(select(func.count()).select_from(ContactMessageRow).where(
            ContactMessageRow.user_id == user_id, ContactMessageRow.created_at >= since)) or 0

    def list(self, open_only: bool = False, limit: int = 200) -> list[ContactMessageDto]:
        """Newest first, with the sender's name and email (None once the account is deleted)."""
        stmt = (select(ContactMessageRow, UserRow.display_name, UserRow.email)
                .outerjoin(UserRow, UserRow.id == ContactMessageRow.user_id)
                .order_by(ContactMessageRow.created_at.desc(), ContactMessageRow.id.desc()).limit(limit))
        if open_only:
            stmt = stmt.where(ContactMessageRow.handled_at.is_(None))
        return [ContactMessageDto(id=m.id, category=m.category, subject=m.subject, body=m.body,
                                  created_at=m.created_at, handled_at=m.handled_at,
                                  user_name=name, user_email=email)
                for m, name, email in self._s.execute(stmt)]

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
