from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SeatOut(BaseModel):
    id: int
    row: str
    number: int
    label: str
    status: str

    model_config = {"from_attributes": True}


class SeatsResponse(BaseModel):
    seats: list[SeatOut]


class CreateHoldRequest(BaseModel):
    user_id: int = Field(..., ge=1)
    seat_ids: list[int] = Field(..., min_length=1, max_length=4)

    @field_validator("seat_ids")
    @classmethod
    def validate_seat_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate seat IDs are not allowed")
        if any(seat_id < 1 for seat_id in value):
            raise ValueError("Seat IDs must be positive integers")
        return value


class HoldSeatOut(BaseModel):
    id: int
    label: str


class HoldOut(BaseModel):
    id: int
    user_id: int
    status: str
    expires_at: datetime
    seats: list[HoldSeatOut]
    created_at: datetime


class CreateBookingRequest(BaseModel):
    hold_id: int = Field(..., ge=1)
    user_id: int = Field(..., ge=1)


class BookingOut(BaseModel):
    id: int
    reference: str
    user_id: int
    hold_id: int
    seats: list[str]
    created_at: datetime


class BookingsResponse(BaseModel):
    bookings: list[BookingOut]


class MessageOut(BaseModel):
    message: str
