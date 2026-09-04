def test_active_hold_can_be_confirmed(client, seat_id_by_label):
    seat_ids = [seat_id_by_label["A10"], seat_id_by_label["A11"]]
    hold = client.post("/holds", json={"user_id": 1, "seat_ids": seat_ids})
    assert hold.status_code == 201

    booking = client.post(
        "/bookings",
        json={"hold_id": hold.json()["id"], "user_id": 1},
    )
    assert booking.status_code == 201
    body = booking.json()
    assert body["reference"].startswith("BOOK-")
    assert set(body["seats"]) == {"A10", "A11"}

    seats = {s["label"]: s["status"] for s in client.get("/seats").json()["seats"]}
    assert seats["A10"] == "booked"
    assert seats["A11"] == "booked"


def test_booking_reference_is_unique(client, seat_id_by_label):
    refs = set()
    for label in ("B10", "B11", "B12"):
        hold = client.post(
            "/holds",
            json={"user_id": 1, "seat_ids": [seat_id_by_label[label]]},
        )
        booking = client.post(
            "/bookings",
            json={"hold_id": hold.json()["id"], "user_id": 1},
        )
        assert booking.status_code == 201
        refs.add(booking.json()["reference"])

    assert len(refs) == 3


def test_list_bookings(client, seat_id_by_label):
    hold = client.post(
        "/holds",
        json={"user_id": 3, "seat_ids": [seat_id_by_label["C10"]]},
    )
    client.post("/bookings", json={"hold_id": hold.json()["id"], "user_id": 3})

    response = client.get("/bookings")
    assert response.status_code == 200
    bookings = response.json()["bookings"]
    assert len(bookings) >= 1
    assert any(b["user_id"] == 3 and "C10" in b["seats"] for b in bookings)
