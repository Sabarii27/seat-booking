import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

# Ensure test DB URL is used before app imports bind the engine.
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "TEST_DATABASE_URL",
        "mysql+pymysql://root:password@localhost:3306/seat_booking_test",
    ),
)

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Booking, Hold, HoldSeat, Seat

get_settings.cache_clear()
settings = get_settings()

# NullPool so concurrent threads each get a real MySQL connection.
engine = create_engine(settings.database_url, pool_pre_ping=True, poolclass=NullPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _mysql_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _mysql_available(),
    reason=(
        "MySQL test database is not available. "
        "Create seat_booking_test and configure DATABASE_URL/TEST_DATABASE_URL."
    ),
)


@pytest.fixture(scope="session", autouse=True)
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        for row in "ABCDEFGHIJ":
            for number in range(1, 13):
                db.add(Seat(row_label=row, seat_number=number, label=f"{row}{number}"))
        db.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_transactional_data() -> Generator[None, None, None]:
    """Remove holds/bookings between tests; keep the 120 seats."""
    yield
    with TestingSessionLocal() as db:
        db.execute(delete(Booking))
        db.execute(delete(HoldSeat))
        db.execute(delete(Hold))
        db.commit()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seat_id_by_label(db: Session) -> dict[str, int]:
    seats = db.query(Seat).all()
    return {seat.label: seat.id for seat in seats}
