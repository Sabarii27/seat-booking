from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models import Booking, Hold, HoldSeat, HoldStatus, Seat
from app.services.expiration import db_now, expire_holds


class SeatUnavailableError(Exception):
    """Raised when one or more requested seats cannot be held."""


def _lock_seats(db: Session, seat_ids: list[int]) -> list[Seat]:
    """
    Lock seat rows in deterministic id order using SELECT ... FOR UPDATE.

    Sorting prevents classic multi-seat deadlocks when two requests lock
    overlapping seats in different orders.
    """
    ordered_ids = sorted(set(seat_ids))
    stmt = (
        select(Seat)
        .where(Seat.id.in_(ordered_ids))
        .order_by(Seat.id)
        .with_for_update()
    )
    seats = list(db.scalars(stmt).all())
    return seats


def _is_seat_booked(db: Session, seat_id: int) -> bool:
    stmt = (
        select(Booking.id)
        .join(Hold, Booking.hold_id == Hold.id)
        .join(HoldSeat, HoldSeat.hold_id == Hold.id)
        .where(HoldSeat.seat_id == seat_id)
        .limit(1)
    )
    return db.scalars(stmt).first() is not None


def _active_hold_for_seat(db: Session, seat_id: int) -> Hold | None:
    now = db_now(db)
    stmt = (
        select(Hold)
        .join(HoldSeat, HoldSeat.hold_id == Hold.id)
        .where(
            HoldSeat.seat_id == seat_id,
            Hold.status == HoldStatus.ACTIVE,
            Hold.expires_at > now,
        )
        .limit(1)
    )
    return db.scalars(stmt).first()


def get_seat_status_map(db: Session, *, commit_expiration: bool = False) -> dict[int, str]:
    """Derive available/held/booked for all seats (after lazy expiration)."""
    expired = expire_holds(db)
    db.flush()
    if commit_expiration and expired:
        db.commit()

    seats = list(db.scalars(select(Seat).order_by(Seat.id)).all())
    status_map = {seat.id: "available" for seat in seats}

    booked_ids = set(
        db.scalars(
            select(HoldSeat.seat_id)
            .join(Hold, HoldSeat.hold_id == Hold.id)
            .join(Booking, Booking.hold_id == Hold.id)
        ).all()
    )
    for seat_id in booked_ids:
        status_map[seat_id] = "booked"

    now = db_now(db)
    held_ids = set(
        db.scalars(
            select(HoldSeat.seat_id)
            .join(Hold, HoldSeat.hold_id == Hold.id)
            .where(
                Hold.status == HoldStatus.ACTIVE,
                Hold.expires_at > now,
            )
        ).all()
    )
    for seat_id in held_ids:
        if status_map.get(seat_id) != "booked":
            status_map[seat_id] = "held"

    return status_map


def list_seats_with_status(db: Session) -> list[dict]:
    # Commit lazy expirations so GET /seats permanently frees seats.
    status_map = get_seat_status_map(db, commit_expiration=True)
    seats = list(db.scalars(select(Seat).order_by(Seat.row_label, Seat.seat_number)).all())
    return [
        {
            "id": seat.id,
            "row": seat.row_label,
            "number": seat.seat_number,
            "label": seat.label,
            "status": status_map[seat.id],
        }
        for seat in seats
    ]


def create_hold(db: Session, *, user_id: int, seat_ids: list[int]) -> Hold:
    """
    Atomically hold 1–4 seats using MySQL row-level locks.

    ALL-OR-NOTHING: if any seat is unavailable, the transaction rolls back
    and no partial hold is created.
    """
    settings = get_settings()
    unique_ids = sorted(set(seat_ids))

    if len(seat_ids) != len(unique_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate seat IDs are not allowed",
        )
    if not 1 <= len(unique_ids) <= 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can hold between 1 and 4 seats",
        )

    try:
        seats = _lock_seats(db, unique_ids)

        if len(seats) != len(unique_ids):
            found = {seat.id for seat in seats}
            missing = [seat_id for seat_id in unique_ids if seat_id not in found]
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat(s) not found: {missing}",
            )

        # Expire relevant holds while seat rows are locked.
        expire_holds(db, seat_ids=unique_ids)
        db.flush()

        for seat in seats:
            if _is_seat_booked(db, seat.id):
                raise SeatUnavailableError(f"Seat {seat.label} is already booked")
            active = _active_hold_for_seat(db, seat.id)
            if active is not None:
                raise SeatUnavailableError(f"Seat {seat.label} is currently held")

        now = db_now(db)
        hold = Hold(
            user_id=user_id,
            status=HoldStatus.ACTIVE,
            expires_at=now + timedelta(seconds=settings.hold_duration_seconds),
        )
        db.add(hold)
        db.flush()

        for seat in seats:
            db.add(HoldSeat(hold_id=hold.id, seat_id=seat.id))

        db.commit()
    except SeatUnavailableError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except OperationalError as exc:
        db.rollback()
        # MySQL deadlock (1213) or lock wait timeout — safe failure for client.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not complete hold due to a concurrent update. Please retry.",
        ) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return get_hold(db, hold.id)


def get_hold(db: Session, hold_id: int) -> Hold:
    hold = db.scalars(
        select(Hold)
        .options(selectinload(Hold.hold_seats).selectinload(HoldSeat.seat))
        .where(Hold.id == hold_id)
    ).first()
    if hold is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")
    return hold


def release_hold(db: Session, *, hold_id: int, user_id: int) -> Hold:
    try:
        hold = db.scalars(
            select(Hold).where(Hold.id == hold_id).with_for_update()
        ).first()
        if hold is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")

        seat_ids = list(
            db.scalars(select(HoldSeat.seat_id).where(HoldSeat.hold_id == hold.id)).all()
        )
        if seat_ids:
            _lock_seats(db, seat_ids)
            expire_holds(db, seat_ids=seat_ids)
            db.refresh(hold)

        if hold.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hold does not belong to this user",
            )

        if hold.status == HoldStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Confirmed holds cannot be released",
            )

        if hold.status == HoldStatus.RELEASED:
            db.commit()
            return get_hold(db, hold.id)

        if hold.status == HoldStatus.EXPIRED:
            db.commit()
            return get_hold(db, hold.id)

        # ACTIVE (and not expired after lazy cleanup)
        now = db_now(db)
        if hold.expires_at <= now:
            hold.status = HoldStatus.EXPIRED
            db.commit()
            return get_hold(db, hold.id)

        hold.status = HoldStatus.RELEASED
        hold.released_at = now
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not release hold due to a concurrent update. Please retry.",
        ) from exc
    except Exception:
        db.rollback()
        raise

    return get_hold(db, hold_id)
