from datetime import timedelta

from sqlalchemy import text

from app.models import Hold, HoldStatus
from app.services.expiration import db_now


def test_hold_available_seats(client, seat_id_by_label):
    seat_ids = [seat_id_by_label["A1"], seat_id_by_label["A2"], seat_id_by_label["A3"]]
    response = client.post("/holds", json={"user_id": 1, "seat_ids": seat_ids})
    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == 1
    assert body["status"] == "ACTIVE"
    assert len(body["seats"]) == 3

    seats = {s["label"]: s["status"] for s in client.get("/seats").json()["seats"]}
    assert seats["A1"] == "held"
    assert seats["A2"] == "held"
    assert seats["A3"] == "held"


def test_cannot_hold_more_than_four_seats(client, seat_id_by_label):
    seat_ids = [
        seat_id_by_label["B1"],
        seat_id_by_label["B2"],
        seat_id_by_label["B3"],
        seat_id_by_label["B4"],
        seat_id_by_label["B5"],
    ]
    response = client.post("/holds", json={"user_id": 1, "seat_ids": seat_ids})
    assert response.status_code == 422


def test_all_or_nothing_hold(client, seat_id_by_label):
    # Book C3 first via hold + booking.
    first = client.post(
        "/holds",
        json={"user_id": 1, "seat_ids": [seat_id_by_label["C3"]]},
    )
    assert first.status_code == 201
    confirm = client.post(
        "/bookings",
        json={"hold_id": first.json()["id"], "user_id": 1},
    )
    assert confirm.status_code == 201

    # Request C1, C2, C3 — must fail entirely.
    response = client.post(
        "/holds",
        json={
            "user_id": 2,
            "seat_ids": [
                seat_id_by_label["C1"],
                seat_id_by_label["C2"],
                seat_id_by_label["C3"],
            ],
        },
    )
    assert response.status_code == 409

    seats = {s["label"]: s["status"] for s in client.get("/seats").json()["seats"]}
    assert seats["C1"] == "available"
    assert seats["C2"] == "available"
    assert seats["C3"] == "booked"


def test_cannot_hold_already_held_seat(client, seat_id_by_label):
    seat_id = seat_id_by_label["D1"]
    first = client.post("/holds", json={"user_id": 1, "seat_ids": [seat_id]})
    assert first.status_code == 201

    second = client.post("/holds", json={"user_id": 2, "seat_ids": [seat_id]})
    assert second.status_code == 409


def test_cannot_hold_booked_seat(client, seat_id_by_label):
    seat_id = seat_id_by_label["E1"]
    hold = client.post("/holds", json={"user_id": 1, "seat_ids": [seat_id]})
    booking = client.post("/bookings", json={"hold_id": hold.json()["id"], "user_id": 1})
    assert booking.status_code == 201

    again = client.post("/holds", json={"user_id": 2, "seat_ids": [seat_id]})
    assert again.status_code == 409


def test_release_hold(client, seat_id_by_label):
    seat_id = seat_id_by_label["F1"]
    hold = client.post("/holds", json={"user_id": 1, "seat_ids": [seat_id]})
    hold_id = hold.json()["id"]

    released = client.delete(f"/holds/{hold_id}", params={"user_id": 1})
    assert released.status_code == 200

    seats = {s["label"]: s["status"] for s in client.get("/seats").json()["seats"]}
    assert seats["F1"] == "available"


def test_different_user_cannot_release_hold(client, seat_id_by_label):
    seat_id = seat_id_by_label["G1"]
    hold = client.post("/holds", json={"user_id": 1, "seat_ids": [seat_id]})
    hold_id = hold.json()["id"]

    response = client.delete(f"/holds/{hold_id}", params={"user_id": 99})
    assert response.status_code == 403


def test_expired_hold_becomes_available(client, seat_id_by_label, db):
    seat_id = seat_id_by_label["H1"]
    hold_resp = client.post("/holds", json={"user_id": 1, "seat_ids": [seat_id]})
    assert hold_resp.status_code == 201
    hold_id = hold_resp.json()["id"]

    hold = db.get(Hold, hold_id)
    hold.expires_at = db_now(db) - timedelta(seconds=1)
    db.commit()

    seats = {s["label"]: s["status"] for s in client.get("/seats").json()["seats"]}
    assert seats["H1"] == "available"


def test_expired_hold_cannot_be_confirmed(client, seat_id_by_label, db):
    seat_id = seat_id_by_label["I1"]
    hold_resp = client.post("/holds", json={"user_id": 1, "seat_ids": [seat_id]})
    hold_id = hold_resp.json()["id"]

    hold = db.get(Hold, hold_id)
    hold.expires_at = db_now(db) - timedelta(seconds=1)
    db.commit()

    booking = client.post("/bookings", json={"hold_id": hold_id, "user_id": 1})
    assert booking.status_code == 409
