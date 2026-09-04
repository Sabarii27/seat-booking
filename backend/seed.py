"""
Idempotent seat seeder.

Creates seats A1–A12 ... J1–J12 (120 seats). Safe to run multiple times.
"""

from sqlalchemy import func, select

from app.database import Base, SessionLocal, engine
from app.models import Seat

ROWS = list("ABCDEFGHIJ")
SEATS_PER_ROW = 12


def seed_seats() -> tuple[int, int]:
    Base.metadata.create_all(bind=engine)
    created = 0

    with SessionLocal() as db:
        for row in ROWS:
            for number in range(1, SEATS_PER_ROW + 1):
                label = f"{row}{number}"
                exists = db.scalars(select(Seat).where(Seat.label == label)).first()
                if exists is not None:
                    continue
                db.add(
                    Seat(
                        row_label=row,
                        seat_number=number,
                        label=label,
                    )
                )
                created += 1
        db.commit()
        total = db.scalar(select(func.count()).select_from(Seat)) or 0

    return created, total


if __name__ == "__main__":
    newly_created, total = seed_seats()
    print(f"Seed complete. Newly created: {newly_created}. Total seats: {total}.")
