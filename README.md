# Seatora

Seatora is a modern seat booking application for one event with a fixed **10 x 12 seat map**. Users can select up to four seats, hold them for five minutes, confirm a booking, or release the hold.

The application uses MySQL transactions and row-level locks to prevent two users from holding or booking the same seat at the same time.

## Features

- 120 seats, from `A1` to `J12`
- Real-time seat status polling every two seconds
- Atomic holds for one to four seats
- Five-minute holds with server-side expiration
- Booking confirmation with unique references such as `BOOK-ADA78B`
- Responsive React interface
- Concurrency tests using real MySQL locking

## Technology

- Backend: Python 3.11+, FastAPI, SQLAlchemy, Pydantic, PyMySQL
- Database: MySQL 8+ with InnoDB
- Frontend: React and Vite
- Tests: pytest, httpx, and ThreadPoolExecutor

## Prerequisites

Install the following before starting:

- Python 3.11 or newer
- Node.js 18 or newer and npm
- MySQL 8 or newer
- Git, if cloning the repository

## 1. Create the MySQL databases

Open MySQL Workbench or the MySQL command-line client and run:

```sql
CREATE DATABASE IF NOT EXISTS seat_booking1
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS seat_booking_test1
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

The application uses `seat_booking1`. The test suite uses `seat_booking_test1`.

## 2. Configure and start the backend

From the project root, open a PowerShell terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `backend/.env` and set your MySQL username and password. Keep the database names as follows:

```text
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/seat_booking1
TEST_DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/seat_booking_test1
HOLD_DURATION_SECONDS=300
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

If your MySQL password contains URL characters such as `#`, `@`, `/`, or `:`, URL-encode the password before placing it in `DATABASE_URL`. For example, `#` becomes `%23`.

Create the tables and seed the 120 seats:

```powershell
$env:PYTHONPATH = "."
python seed.py
```

Start the API and leave this terminal running:

```powershell
uvicorn app.main:app --reload
```

The backend is available at:

- API: http://127.0.0.1:8000
- Health check: http://127.0.0.1:8000/health
- Swagger documentation: http://127.0.0.1:8000/docs

You should see `{"status":"ok"}` from the health check.

## 3. Start the frontend

Open a second terminal from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally:

http://localhost:5173

The Vite development server proxies API requests to the FastAPI server on port 8000.

## Using the application

1. Select one to four green available seats.
2. Click **Hold Selected Seats**.
3. Confirm the booking before the five-minute timer expires, or release the hold.
4. Confirmed bookings are stored in the `bookings` table.

Check stored data in MySQL with:

```sql
USE seat_booking1;

SELECT * FROM seats;
SELECT * FROM holds;
SELECT * FROM hold_seats;
SELECT * FROM bookings;
```

Released and expired holds remain in the database for history. Their status changes to `RELEASED` or `EXPIRED`.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check that the API is running |
| `GET` | `/seats` | Return all seats and their current status |
| `POST` | `/holds` | Create an atomic hold for one to four seats |
| `DELETE` | `/holds/{hold_id}?user_id={user_id}` | Release a hold |
| `POST` | `/bookings` | Confirm a hold as a booking |
| `GET` | `/bookings` | List confirmed bookings |

## Concurrency design

Concurrency is the central correctness requirement. A simple implementation that first checks whether a seat is available and then inserts a hold has a race:

```text
Request A: checks seat 1 -> available
Request B: checks seat 1 -> available
Request A: inserts a hold
Request B: inserts another hold
```

Both requests can observe the same old state, resulting in a double hold. The application avoids that race with MySQL InnoDB row locks:

1. Validate that the request contains one to four unique seat IDs.
2. Sort the seat IDs and select those `seats` rows with `SELECT ... FOR UPDATE`.
3. Keep those locks until the transaction finishes. A competing request for an overlapping seat waits at this point.
4. Expire old holds for the locked seats, then re-check booked seats and active holds while the locks are still held.
5. If any seat is unavailable, roll back the entire transaction and return HTTP `409`. No partial hold remains.
6. Otherwise insert one `holds` row and its `hold_seats` rows, then commit once.

Sorting the IDs gives every multi-seat request the same lock order. For example, requests for `[2, 1]` and `[1, 2]` both lock `1` before `2`, which reduces the chance of a deadlock. If MySQL still reports a deadlock or lock-wait timeout, the service rolls back and returns a retryable `409` response.

Booking confirmation uses the same principle at the hold level. It locks the hold row with `FOR UPDATE`, locks its seat rows, checks that the hold is still active and belongs to the user, changes the hold to `CONFIRMED`, and inserts the booking in one transaction. The database also enforces `UNIQUE(hold_id)` on `bookings`, providing a second guard against two confirmations of the same hold.

### How concurrency is tested

`backend/tests/test_concurrency.py` runs two real threads with separate SQLAlchemy sessions against MySQL:

- Two requests try to hold the same seat. The expected result is exactly one HTTP `201` and one HTTP `409`.
- Two requests try to confirm the same hold. The expected result is exactly one HTTP `201`, one HTTP `409`, and exactly one booking row.

These tests call the service layer directly because that is where the database transaction and `FOR UPDATE` lock run. A sequential or serialized HTTP test would not prove lock contention. SQLite is not an acceptable substitute for these tests because its locking behavior is different from MySQL InnoDB.

## Run the tests

Make sure MySQL is running and `backend/.env` contains a valid `TEST_DATABASE_URL`. From `backend/`:

```powershell
\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
pytest -v
```

The concurrency tests require MySQL. A missing or unreachable test database causes the suite to skip with a clear reason rather than falsely claiming that concurrency was verified.

## Implemented and intentionally missing

Implemented for this assessment:

- Atomic multi-seat holds with all-or-nothing rollback
- Deterministic row-lock ordering to reduce deadlocks
- Lazy expiration using the database clock
- Ownership checks for hold release and confirmation
- One-booking-per-hold database constraint
- Real MySQL concurrency tests for competing holds and confirmations

Not implemented yet:

- Authentication and authorization beyond the demo `user_id`
- Multiple events or venues
- Database migrations with Alembic
- Background cleanup worker
- WebSockets or server-sent events; the UI currently polls every two seconds
- Production deployment, observability, rate limiting, and HTTPS configuration

These are deliberate scope limits, not unverified claims about production readiness.

## Troubleshooting

### `Unknown database`

Run the database creation SQL from step 1 and check that the database name in `.env` is exactly `seat_booking1`.

### `Unknown column` or missing table errors

Run `python seed.py` from the `backend` directory. The project expects a schema created from the current SQLAlchemy models. `create_all()` does not migrate an old schema.

### Frontend cannot load seats

Confirm both servers are running, then visit http://127.0.0.1:8000/health. If it does not return `{"status":"ok"}`, restart the backend from the activated virtual environment.

### PowerShell blocks activation

Run PowerShell as your normal user and execute:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate the environment again.

## Project structure

```text
seat-booking/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── tests/
│   ├── seed.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── README.md
└── PROMPTS.md
```

## Important production considerations

This is an assessment and portfolio project. Before production use, add authentication, authorization, database migrations with Alembic, structured logging, monitoring, rate limiting, deployment configuration, and HTTPS.

