import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HoldStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"
    CONFIRMED = "CONFIRMED"


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("row_label", "seat_number", name="uq_seat_row_number"),
        UniqueConstraint("label", name="uq_seat_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    row_label: Mapped[str] = mapped_column(String(1), nullable=False)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    hold_seats: Mapped[list["HoldSeat"]] = relationship(back_populates="seat")


class Hold(Base):
    __tablename__ = "holds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[HoldStatus] = mapped_column(
        Enum(HoldStatus),
        nullable=False,
        default=HoldStatus.ACTIVE,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    hold_seats: Mapped[list["HoldSeat"]] = relationship(
        back_populates="hold",
        cascade="all, delete-orphan",
    )
    booking: Mapped["Booking | None"] = relationship(back_populates="hold", uselist=False)


class HoldSeat(Base):
    __tablename__ = "hold_seats"

    hold_id: Mapped[int] = mapped_column(
        ForeignKey("holds.id", ondelete="CASCADE"),
        primary_key=True,
    )
    seat_id: Mapped[int] = mapped_column(
        ForeignKey("seats.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )

    hold: Mapped[Hold] = relationship(back_populates="hold_seats")
    seat: Mapped[Seat] = relationship(back_populates="hold_seats")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hold_id: Mapped[int] = mapped_column(
        ForeignKey("holds.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    booking_reference: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    hold: Mapped[Hold] = relationship(back_populates="booking")
