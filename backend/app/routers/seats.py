from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SeatOut, SeatsResponse
from app.services import hold_service

router = APIRouter(prefix="/seats", tags=["seats"])


@router.get("", response_model=SeatsResponse)
def get_seats(db: Session = Depends(get_db)) -> SeatsResponse:
    seats = hold_service.list_seats_with_status(db)
    return SeatsResponse(seats=[SeatOut(**seat) for seat in seats])
