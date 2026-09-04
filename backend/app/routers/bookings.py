from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import BookingOut, BookingsResponse, CreateBookingRequest
from app.services import booking_service

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _serialize_booking(booking) -> BookingOut:
    seats = sorted(
        (hs.seat.label for hs in booking.hold.hold_seats),
        key=lambda label: label,
    )
    return BookingOut(
        id=booking.id,
        reference=booking.booking_reference,
        user_id=booking.user_id,
        hold_id=booking.hold_id,
        seats=seats,
        created_at=booking.created_at,
    )


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(payload: CreateBookingRequest, db: Session = Depends(get_db)) -> BookingOut:
    booking = booking_service.create_booking(
        db,
        hold_id=payload.hold_id,
        user_id=payload.user_id,
    )
    return _serialize_booking(booking)


@router.get("", response_model=BookingsResponse)
def list_bookings(db: Session = Depends(get_db)) -> BookingsResponse:
    bookings = booking_service.list_bookings(db)
    return BookingsResponse(bookings=[_serialize_booking(b) for b in bookings])
