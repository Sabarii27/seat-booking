from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, Hold, HoldSeat, HoldStatus
from app.services.expiration import db_now, expire_holds
from app.services.hold_service import _lock_seats, get_hold
from app.utils.booking_reference import generate_booking_reference


def create_booking(db: Session, *, hold_id: int, user_id: int) -> Booking:
    """
    Confirm an ACTIVE, non-expired hold into a permanent booking.

    The hold row is locked with FOR UPDATE so two concurrent confirmations
    of the same hold cannot both succeed. UNIQUE(hold_id) is a second guard.
    """
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
                detail="Hold has already been confirmed",
            )

        if hold.status in (HoldStatus.RELEASED, HoldStatus.EXPIRED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Hold is {hold.status.value.lower()} and cannot be confirmed",
            )

        now = db_now(db)
        if hold.status != HoldStatus.ACTIVE or hold.expires_at <= now:
            hold.status = HoldStatus.EXPIRED
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Hold has expired and cannot be confirmed",
            )

        booking = Booking(
            hold_id=hold.id,
            user_id=user_id,
            booking_reference=generate_booking_reference(),
        )
        hold.status = HoldStatus.CONFIRMED
        db.add(booking)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hold has already been confirmed",
        ) from exc
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not confirm booking due to a concurrent update. Please retry.",
        ) from exc
    except Exception:
        db.rollback()
        raise

    return get_booking(db, booking.id)


def get_booking(db: Session, booking_id: int) -> Booking:
    booking = db.scalars(
        select(Booking)
        .options(
            selectinload(Booking.hold)
            .selectinload(Hold.hold_seats)
            .selectinload(HoldSeat.seat)
        )
        .where(Booking.id == booking_id)
    ).first()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


def list_bookings(db: Session) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking)
            .options(
                selectinload(Booking.hold)
                .selectinload(Hold.hold_seats)
                .selectinload(HoldSeat.seat)
            )
            .order_by(Booking.id)
        ).all()
    )
