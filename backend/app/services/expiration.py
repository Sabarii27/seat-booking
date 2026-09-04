from datetime import datetime

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.models import Hold, HoldSeat, HoldStatus


def db_now(db: Session) -> datetime:
    """Return current MySQL database time (authoritative clock)."""
    return db.execute(text("SELECT NOW(6)")).scalar_one()


def expire_holds(db: Session, *, seat_ids: list[int] | None = None) -> int:
    """
    Lazy-expire ACTIVE holds whose expires_at has passed.

    If seat_ids is provided, only expire holds that touch those seats
    (still safe under seat row locks). Otherwise expire all overdue holds.
    """
    now = db_now(db)

    query = select(Hold.id).where(
        Hold.status == HoldStatus.ACTIVE,
        Hold.expires_at <= now,
    )

    if seat_ids is not None:
        query = (
            query.join(HoldSeat, HoldSeat.hold_id == Hold.id)
            .where(HoldSeat.seat_id.in_(seat_ids))
            .distinct()
        )

    expired_ids = list(db.scalars(query).all())
    if not expired_ids:
        return 0

    result = db.execute(
        update(Hold)
        .where(Hold.id.in_(expired_ids), Hold.status == HoldStatus.ACTIVE)
        .values(status=HoldStatus.EXPIRED)
    )
    return result.rowcount or 0
