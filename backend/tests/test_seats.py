def test_exactly_120_seats(client):
    response = client.get("/seats")
    assert response.status_code == 200
    seats = response.json()["seats"]
    assert len(seats) == 120


def test_seat_labels_are_correct(client):
    response = client.get("/seats")
    seats = response.json()["seats"]
    labels = {seat["label"] for seat in seats}

    expected = {f"{row}{number}" for row in "ABCDEFGHIJ" for number in range(1, 13)}
    assert labels == expected

    sample = next(seat for seat in seats if seat["label"] == "A1")
    assert sample["row"] == "A"
    assert sample["number"] == 1
    assert sample["status"] == "available"
