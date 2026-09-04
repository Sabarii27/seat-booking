from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CreateHoldRequest, HoldOut, HoldSeatOut, MessageOut
from app.services import hold_service

router = APIRouter(prefix="/holds", tags=["holds"])


def _serialize_hold(hold) -> HoldOut:
    return HoldOut(
        id=hold.id,
        user_id=hold.user_id,
        status=hold.status.value,
        expires_at=hold.expires_at,
        created_at=hold.created_at,
        seats=[
            HoldSeatOut(id=hs.seat.id, label=hs.seat.label)
            for hs in sorted(hold.hold_seats, key=lambda item: item.seat_id)
        ],
    )


@router.post("", response_model=HoldOut, status_code=status.HTTP_201_CREATED)
def create_hold(payload: CreateHoldRequest, db: Session = Depends(get_db)) -> HoldOut:
    hold = hold_service.create_hold(
        db,
        user_id=payload.user_id,
        seat_ids=payload.seat_ids,
    )
    return _serialize_hold(hold)


@router.delete("/{hold_id}", response_model=MessageOut)
def release_hold(
    hold_id: int,
    user_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> MessageOut:
    hold = hold_service.release_hold(db, hold_id=hold_id, user_id=user_id)
    return MessageOut(message=f"Hold {hold.id} is now {hold.status.value}")
