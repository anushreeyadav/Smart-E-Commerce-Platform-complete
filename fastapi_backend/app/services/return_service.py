from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import RETURN_WINDOW_DAYS
from app.models.order import Order, OrderStatus
from app.models.return_request import ReturnRequest, ReturnRequestStatus
from app.models.return_request_history import ReturnRequestHistory
from app.models.user import User


def get_return_request_for_order(db: Session, order_id: str) -> ReturnRequest | None:
    return db.query(ReturnRequest).filter(ReturnRequest.order_id == order_id).first()


def get_return_request_by_id(db: Session, return_request_id: str) -> ReturnRequest | None:
    return (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_request_id)
        .first()
    )


def record_return_request_history(
    db: Session,
    *,
    return_request: ReturnRequest,
    previous_status: ReturnRequestStatus | None,
    new_status: ReturnRequestStatus,
    changed_by: str | None,
    comment: str | None = None,
) -> None:
    db.add(
        ReturnRequestHistory(
            return_request_id=return_request.id,
            previous_status=previous_status.value if previous_status else None,
            new_status=new_status.value,
            comment=comment,
            changed_by=changed_by,
        )
    )


def review_return_request(
    db: Session,
    *,
    return_request: ReturnRequest,
    reviewer: User,
    decision: ReturnRequestStatus,
    comment: str | None = None,
) -> ReturnRequest:
    """Approve or reject a pending return request. Preserves the customer's
    original reason/comments and appends to the request's audit history."""

    if return_request.status != ReturnRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This return request was already {return_request.status.value} "
                "and cannot be processed again."
            ),
        )

    previous_status = return_request.status
    return_request.status = decision
    return_request.reviewed_by = reviewer.id
    return_request.reviewed_at = datetime.now(timezone.utc)
    return_request.review_comment = comment.strip() if comment else None

    record_return_request_history(
        db,
        return_request=return_request,
        previous_status=previous_status,
        new_status=decision,
        changed_by=reviewer.id,
        comment=return_request.review_comment,
    )

    db.commit()
    db.refresh(return_request)
    return return_request


def return_window_expires_at(order: Order) -> datetime | None:
    if not order.delivered_at:
        return None
    delivered_at = order.delivered_at
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=timezone.utc)
    return delivered_at + timedelta(days=RETURN_WINDOW_DAYS)


def is_return_eligible(order: Order, now: datetime | None = None) -> bool:
    expires_at = return_window_expires_at(order)
    if order.status != OrderStatus.DELIVERED or not expires_at:
        return False
    return (now or datetime.now(timezone.utc)) <= expires_at


def validate_return_request(order: Order) -> None:
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only delivered orders can be returned")
    if not is_return_eligible(order):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The return window has expired")
