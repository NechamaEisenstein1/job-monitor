"""Points ledger and subscriptions. Balances change only through conditional UPDATEs, so
two concurrent spends can never overdraw an account. Nothing here commits: the use case
commits once, keeping a posting and its point award (or a purchase and its charge) atomic."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.domain.enums import PointAction, SubscriptionStatus
from backend.domain.models import PointTransaction, Subscription
from backend.infrastructure.db.orm import PointTransactionRow, SubscriptionRow, UserRow
from backend.infrastructure.repositories.mapping import to_domain, to_values

_TX_ENUMS = {"action_type": PointAction}
_SUB_ENUMS = {"status": SubscriptionStatus}


class InsufficientPointsError(Exception):
    pass


class SqlBillingRepository:
    def __init__(self, session: Session):
        self._s = session

    def commit(self) -> None:
        self._s.commit()

    def rollback(self) -> None:
        self._s.rollback()

    # ------------------------------------------------------------- points

    def balance(self, user_id: int) -> int:
        return self._s.scalar(select(UserRow.points_balance).where(UserRow.id == user_id)) or 0

    def apply(self, user_id: int, amount: int, action: PointAction, now: datetime, *,
              reference: str | None = None, allow_negative: bool = False) -> PointTransaction:
        """Move points and log it. Spending more than the balance raises
        InsufficientPointsError unless allow_negative (admin reversals may leave a debt)."""
        stmt = update(UserRow).where(UserRow.id == user_id).values(
            points_balance=UserRow.points_balance + amount)
        if amount < 0 and not allow_negative:
            stmt = stmt.where(UserRow.points_balance + amount >= 0)
        if self._s.execute(stmt.execution_options(synchronize_session=False)).rowcount != 1:
            raise InsufficientPointsError(f"user {user_id} cannot spend {-amount} points")
        tx = PointTransaction(id=None, user_id=user_id, amount=amount, action_type=action,
                              created_at=now, reference=reference)
        row = PointTransactionRow(**to_values(tx))
        self._s.add(row)
        self._s.flush()
        tx.id = row.id
        return tx

    def history(self, user_id: int, limit: int = 50) -> list[PointTransaction]:
        rows = self._s.scalars(select(PointTransactionRow).where(PointTransactionRow.user_id == user_id)
                               .order_by(PointTransactionRow.created_at.desc(), PointTransactionRow.id.desc())
                               .limit(limit))
        return [to_domain(r, PointTransaction, _TX_ENUMS) for r in rows]

    def awarded_posts_since(self, user_id: int, since: datetime) -> int:
        return self._s.scalar(select(func.count()).select_from(PointTransactionRow).where(
            PointTransactionRow.user_id == user_id,
            PointTransactionRow.action_type == PointAction.JOB_POSTED.value,
            PointTransactionRow.created_at >= since)) or 0

    def award_for(self, reference: str) -> PointTransaction | None:
        row = self._s.scalars(select(PointTransactionRow).where(
            PointTransactionRow.reference == reference,
            PointTransactionRow.action_type == PointAction.JOB_POSTED.value)).first()
        return to_domain(row, PointTransaction, _TX_ENUMS) if row else None

    # ------------------------------------------------------------- subscriptions

    def add_subscription(self, sub: Subscription) -> Subscription:
        row = SubscriptionRow(**to_values(sub))
        self._s.add(row)
        self._s.flush()
        sub.id = row.id
        return sub

    def current_subscription(self, user_id: int, now: datetime) -> Subscription | None:
        row = self._s.scalars(select(SubscriptionRow).where(
            SubscriptionRow.user_id == user_id, SubscriptionRow.starts_at <= now, SubscriptionRow.expires_at > now,
        ).order_by(SubscriptionRow.expires_at.desc()).limit(1)).first()
        return to_domain(row, Subscription, _SUB_ENUMS) if row else None

    def latest_expiry(self, user_id: int) -> datetime | None:
        return self._s.scalar(select(func.max(SubscriptionRow.expires_at)).where(SubscriptionRow.user_id == user_id))

    def had_trial(self, user_id: int) -> bool:
        return self._s.scalar(select(func.count()).select_from(SubscriptionRow).where(
            SubscriptionRow.user_id == user_id, SubscriptionRow.status == SubscriptionStatus.TRIAL.value)) > 0

    def list_subscriptions(self, user_id: int) -> list[Subscription]:
        rows = self._s.scalars(select(SubscriptionRow).where(SubscriptionRow.user_id == user_id)
                               .order_by(SubscriptionRow.created_at.desc()))
        return [to_domain(r, Subscription, _SUB_ENUMS) for r in rows]

    def stored_status(self, user_id: int) -> SubscriptionStatus:
        value = self._s.scalar(select(UserRow.subscription_status).where(UserRow.id == user_id))
        return SubscriptionStatus(value or SubscriptionStatus.INACTIVE.value)

    def set_status(self, user_id: int, status: SubscriptionStatus) -> None:
        self._s.execute(update(UserRow).where(UserRow.id == user_id)
                        .values(subscription_status=status.value).execution_options(synchronize_session=False))
