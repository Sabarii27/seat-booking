"""
Concurrency tests against real MySQL.

These tests open separate SQLAlchemy sessions on separate threads so two
transactions contend for the same InnoDB row locks at the same time.

We call the service layer directly (not sequential HTTP) because that is
where SELECT ... FOR UPDATE runs. FastAPI's TestClient can serialize
requests and would not prove MySQL concurrency.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import HTTPException

from app.services import booking_service, hold_service
from tests.conftest import TestingSessionLocal


def test_concurrent_hold_same_seat(seat_id_by_label):
    seat_id = seat_id_by_label["J1"]

    def attempt(user_id: int) -> int:
        db = TestingSessionLocal()
        try:
            hold_service.create_hold(db, user_id=user_id, seat_ids=[seat_id])
            return 201
        except HTTPException as exc:
            return exc.status_code
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt, 1), pool.submit(attempt, 2)]
        statuses = [future.result() for future in as_completed(futures)]

    successes = statuses.count(201)
    conflicts = statuses.count(409)

    assert successes == 1, f"Expected exactly one success, got statuses={statuses}"
    assert conflicts == 1, f"Expected exactly one conflict, got statuses={statuses}"


def test_concurrent_confirm_same_hold(seat_id_by_label):
    seat_id = seat_id_by_label["J2"]

    setup_db = TestingSessionLocal()
    try:
        hold = hold_service.create_hold(setup_db, user_id=1, seat_ids=[seat_id])
        hold_id = hold.id
    finally:
        setup_db.close()

    def attempt() -> int:
        db = TestingSessionLocal()
        try:
            booking_service.create_booking(db, hold_id=hold_id, user_id=1)
            return 201
        except HTTPException as exc:
            return exc.status_code
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt), pool.submit(attempt)]
        statuses = [future.result() for future in as_completed(futures)]

    successes = statuses.count(201)
    conflicts = statuses.count(409)

    assert successes == 1, f"Expected exactly one booking success, got statuses={statuses}"
    assert conflicts == 1, f"Expected exactly one booking conflict, got statuses={statuses}"

    verify_db = TestingSessionLocal()
    try:
        bookings = booking_service.list_bookings(verify_db)
        matching = [b for b in bookings if b.hold_id == hold_id]
        assert len(matching) == 1
    finally:
        verify_db.close()
