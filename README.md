# Seat Booking System

Technical assessment project for **Compunet Connections**: a concurrent-safe ticket booking app for a single event with a fixed **10 × 12 (120 seat)** map.

## Overview

Users view a seat map, select up to **4** available seats, place a **5-minute hold**, then confirm a booking or release the hold. The backend uses **MySQL InnoDB transactions** and **`SELECT ... FOR UPDATE`** so a seat can never be sold twice.

## Features

- 120 seats (A1–J12) with derived statuses: `available`, `held`, `booked`
- Atomic all-or-nothing multi-seat holds (1–4 seats)
- 5-minute holds with lazy server-side expiration
- Booking confirmation with unique references (`BOOK-XXXXXX`)
- React seat map with selection, countdown, release/confirm, and 2s polling
- pytest suite including real concurrent MySQL hold/confirm tests

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic, PyMySQL |
| Database | MySQL 8+ |
| Frontend | React, Vite, JavaScript |
| Tests | pytest, httpx, ThreadPoolExecutor |

## Architecture

```text
Browser (React)  --HTTP/JSON-->  FastAPI  --SQLAlchemy-->  MySQL 8 (InnoDB)
                     ^
                     |  poll GET /seats every 2s
```

- **Routers** expose HTTP endpoints.
- **Services** own transactions, locking, and business rules.
- Seat status is **derived** from holds/bookings (not a mutable column on `seats`).

## Project Structure

```text
seat-booking/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routers/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── seed.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
├── README.md
├── PROMPTS.md
└── .gitignore
```

## Database Schema

### `seats`
Physical seats. Unique `(row_label, seat_number)` and unique `label` (e.g. `A1`).

### `holds`
Temporary reservations. Status: `ACTIVE`, `EXPIRED`, `RELEASED`, `CONFIRMED`. `expires_at` is authoritative.

### `hold_seats`
Join table linking a hold to 1–4 seats. PK `(hold_id, seat_id)`.

### `bookings`
Permanent confirmation of a hold. `hold_id` is unique (one booking per hold). `booking_reference` is unique.

## Setup Instructions

### 1. Clone / open the project

```bash
cd seat-booking
```

### 2. MySQL

Create databases:

```sql
CREATE DATABASE seat_booking CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE seat_booking_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Backend

```bash
cd backend
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your MySQL credentials:

```text
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/seat_booking
TEST_DATABASE_URL=mysql+pymysql://root:password@localhost:3306/seat_booking_test
```

Seed seats (idempotent):

```bash
python seed.py
```

Run API:

```bash
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

Vite proxies API calls to the FastAPI server.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/seats` | All seats + derived status |
| `POST` | `/holds` | Atomic hold (1–4 seats), 5 minutes |
| `DELETE` | `/holds/{id}?user_id=` | Release hold |
| `POST` | `/bookings` | Confirm hold → booking |
| `GET` | `/bookings` | List bookings |

## Concurrency and Double-Booking Prevention

### Problem

This pattern is unsafe under concurrency:

```text
check availability
insert hold
```

Two transactions can both observe a seat as free, then both insert holds → **double booking**.

### Solution

Holds run inside a MySQL transaction:

1. Start transaction
2. Sort requested seat IDs (deterministic lock order)
3. `SELECT ... FROM seats WHERE id IN (...) ORDER BY id FOR UPDATE`
4. Lazy-expire overdue holds that touch those seats
5. Recheck booked / actively held while locks are held
6. If any seat is unavailable → `ROLLBACK` → HTTP 409
7. Else insert hold + hold_seats → `COMMIT` → HTTP 201

### Example

```text
Transaction A                    Transaction B
     ↓                                ↓
locks seat 1                     tries to lock seat 1
     ↓                                ↓
checks availability                   WAITS
     ↓
creates hold
     ↓
COMMIT
                                      ↓
                                 obtains lock
                                      ↓
                                 sees seat held
                                      ↓
                                 ROLLBACK → 409
```

Exactly one request succeeds. Deterministic `ORDER BY id` reduces deadlocks when requests lock overlapping seats in different request orders (e.g. `[A2,A1]` vs `[A1,A2]`).

Booking confirmation locks the hold row with `FOR UPDATE` and also relies on `UNIQUE(hold_id)` on `bookings`.

## Hold Expiration

- Every hold lasts **5 minutes** (`HOLD_DURATION_SECONDS=300`).
- The **backend/database clock** is authoritative.
- The frontend countdown is **display only**.
- **Lazy expiration**: on seat reads and hold/booking writes, `ACTIVE` holds with `expires_at <= NOW()` are marked `EXPIRED`.
- No background worker is required for this assessment.

## Polling

The frontend polls `GET /seats` every **2 seconds** (`POLL_INTERVAL = 2000` in `App.jsx`).

We chose a 2-second polling interval because this is a small assessment application and polling is significantly simpler than introducing WebSockets. It provides near-real-time seat updates while keeping implementation and infrastructure simple.

In production, WebSockets or Server-Sent Events could replace polling.

## Testing

From `backend/` with MySQL `seat_booking_test` configured:

```bash
pytest -v
```

Important concurrency tests (`tests/test_concurrency.py`):

- Two threads hold the **same seat** → assert exactly **one** `201` and one `409`
- Two threads confirm the **same hold** → assert exactly **one** booking

These run against **MySQL** (not SQLite). SQLite locking is different and would not prove InnoDB correctness. Tests use separate SQLAlchemy sessions on threads so real row-lock contention occurs.

## Future Improvements

Not implemented (intentionally):

- Authentication / authorization
- Multiple events / venues
- WebSockets or SSE
- Background cleanup worker
- Alembic migrations
- Structured logging and monitoring
- Rate limiting
- Load testing
- Production deployment hardening
- Richer UI/UX

## AI Usage

Development used AI assistance. See [`PROMPTS.md`](PROMPTS.md) for an honest prompt/decision log.
