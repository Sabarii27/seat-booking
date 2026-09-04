# AI Development Log

This file records how AI was used while building the Compunet Connections Seat Booking System. Prompts are summarized; results and human decisions are called out honestly.

## Prompt 1 — Architecture

**Prompt:**  
Master requirements for a FastAPI + MySQL + React seat booking system with atomic holds, no double booking, lazy expiration, and phased delivery. Start with Phase 1 plan only.

**Result:**  
Proposed derived seat status (not a status column), `SELECT … FOR UPDATE` with sorted seat IDs, lazy expiration, thin routers + service layer, 2s polling UI.

**Changes I made:**  
Accepted the plan. Later asked to build the **full project in one go** instead of stopping after Phase 1.

---

## Prompt 2 — Database Design

**Prompt (embedded in master spec):**  
Tables for seats, holds, hold_seats, bookings with uniqueness constraints.

**Result:**  
SQLAlchemy models matching the suggested schema; booking tied 1:1 to a confirmed hold via `UNIQUE(hold_id)`.

**Changes I made:**  
Used `row_label` instead of ambiguous `row_number` for A–J. Kept status off the `seats` table so availability cannot drift from holds/bookings.

---

## Prompt 3 — Concurrency

**Prompt:**  
Explain MySQL `FOR UPDATE`, deadlocks, and implement holds that cannot double-book.

**Result:**  
Hold service locks seats in ascending id order, expires relevant holds under those locks, checks availability, then inserts hold + hold_seats in one transaction.

**Changes I made:**  
On InnoDB deadlock / lock wait errors, return HTTP 409 with a retry message instead of a 500. Documented that TestClient can serialize HTTP calls, so concurrency tests use **threaded service calls with separate DB sessions** against MySQL for a real proof.

---

## Prompt 4 — Backend

**Prompt:**  
Implement FastAPI endpoints, seed script, env config, validation.

**Result:**  
Routers for seats/holds/bookings; seed A1–J12; pydantic validation for 1–4 unique seat IDs.

**Changes I made:**  
Release endpoint takes `user_id` as a query param (auth out of scope). Confirmed holds cannot be released. Expired holds are handled safely on release/confirm.

---

## Prompt 5 — Testing

**Prompt:**  
pytest coverage including concurrent same-seat hold and concurrent confirm.

**Result:**  
Tests for seats, holds, bookings, expiration, ownership, uniqueness, and concurrency.

**Changes I made:**  
Dedicated `seat_booking_test` database via `DATABASE_URL`/`TEST_DATABASE_URL`. Skip suite with a clear reason if MySQL is unreachable. Prefer service-level concurrency over claiming SQLite proves MySQL safety.

---

## Prompt 6 — Frontend

**Prompt:**  
Simple React seat map, hold countdown, confirm/release, 2s polling, 409 handling.

**Result:**  
Vite + React JS components; configurable `POLL_INTERVAL`; stale selection cleared after 409.

**Changes I made:**  
Kept styling plain and functional. Used Vite proxy to avoid CORS friction in local dev while still enabling CORS on the API.

---

## Prompt 7 — Debugging / corrections during generation

**Issues found while assembling the project:**

1. **Lazy expiration not committed on `GET /seats`**  
   Expiration updates were flushed but not committed when the request session closed.  
   **Fix:** commit expiration changes when listing seats.

2. **Concurrency test honesty**  
   Using only sequential HTTP calls (or a single-threaded TestClient path) would not prove locking.  
   **Fix:** `ThreadPoolExecutor` + separate MySQL sessions calling hold/booking services.

3. **Shell unavailable in the agent environment**  
   Could not run `pip`/`pytest`/`npm`/`git` from the agent terminal during this session.  
   **Fix:** shipped complete source + setup commands for local verification; user must run install/seed/test locally.

---

## AI Mistakes and Corrections

| Mistake | Correction |
|---------|------------|
| Almost left expiration uncommitted on seat reads | Commit after lazy expire in `list_seats_with_status` |
| Risk of overstating HTTP TestClient concurrency | Test at transaction/service layer on MySQL threads |
| Original phased “wait after Phase 1” | User instructed to deliver the full folder; proceeded end-to-end |

No invented failures: only issues noticed while implementing this project.
