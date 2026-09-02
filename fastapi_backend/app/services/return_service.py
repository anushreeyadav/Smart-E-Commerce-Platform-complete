from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import RETURN_WINDOW_DAYS
from app.core.stripe_client import get_stripe_client
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import PaymentStatus
from app.models.product import Product
from app.models.return_request import ReturnRequest, ReturnRequestStatus
from app.models.return_request_history import ReturnRequestHistory
from app.models.user import User
from app.services.order_service import get_payment_by_order_id


def get_return_request_for_order(db: Session, order_id: str) -> ReturnRequest | None:
    return db.query(ReturnRequest).filter(ReturnRequest.order_id == order_id).first()


def get_return_request_by_id(db: Session, return_request_id: str) -> ReturnRequest | None:
    return (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_request_id)
        .first()
    )


def list_return_requests_filtered(
    db: Session,
    *,
    status_filter: ReturnRequestStatus | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ReturnRequest], int]:
    query = (
        db.query(ReturnRequest)
        .join(User, User.id == ReturnRequest.user_id)
        .options(
            joinedload(ReturnRequest.user),
            joinedload(ReturnRequest.reviewer),
            selectinload(ReturnRequest.history),
        )
    )

    if status_filter:
        query = query.filter(ReturnRequest.status == status_filter)

    if search:
        like_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ReturnRequest.id.ilike(like_pattern),
                ReturnRequest.order_id.ilike(like_pattern),
                User.name.ilike(like_pattern),
                User.email.ilike(like_pattern),
            )
        )

    total = query.count()

    return_requests = (
        query.order_by(ReturnRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return return_requests, total


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


# The return request lifecycle. "pending" is the customer-facing "Requested"
# state. rejected/refunded are terminal - nothing can move out of them.
RETURN_STATUS_TRANSITIONS: dict[ReturnRequestStatus, set[ReturnRequestStatus]] = {
    ReturnRequestStatus.PENDING: {ReturnRequestStatus.APPROVED, ReturnRequestStatus.REJECTED},
    ReturnRequestStatus.APPROVED: {ReturnRequestStatus.RETURNED},
    ReturnRequestStatus.RETURNED: {ReturnRequestStatus.REFUNDED},
    ReturnRequestStatus.REJECTED: set(),
    ReturnRequestStatus.REFUNDED: set(),
}


def validate_return_status_transition(
    current_status: ReturnRequestStatus,
    target_status: ReturnRequestStatus,
) -> None:
    """Raise 400 unless moving from current_status to target_status is a
    legal step in the return lifecycle. Re-requesting the current status
    (a duplicate/repeated update) is also rejected."""

    if current_status == target_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This return request is already '{current_status.value}'.",
        )

    if target_status not in RETURN_STATUS_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot move a return request from '{current_status.value}' "
                f"to '{target_status.value}'."
            ),
        )


def restock_return_items(db: Session, *, order_id: str) -> list[dict]:
    """Return an order's items to inventory. Called exactly once, from
    review_return_request when a return moves pending -> approved. Safe
    against double-restocking: validate_return_status_transition already
    refuses to re-approve a return that isn't 'pending', so this can't run
    twice for the same return request."""

    rows = (
        db.query(OrderItem, Product)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(OrderItem.order_id == order_id)
        .all()
    )

    restocked = []

    for order_item, product in rows:
        product.stock += order_item.quantity
        restocked.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "quantity": order_item.quantity,
                "new_stock": product.stock,
            }
        )

    return restocked


def review_return_request(
    db: Session,
    *,
    return_request: ReturnRequest,
    reviewer: User,
    decision: ReturnRequestStatus,
    comment: str | None = None,
) -> ReturnRequest:
    """Approve or reject a pending return request. Preserves the customer's
    original reason/comments and appends to the request's audit history.
    Approving also restocks the returned items - in the same transaction as
    the status change, so a restock failure rolls back the approval too."""

    validate_return_status_transition(return_request.status, decision)

    previous_status = return_request.status
    return_request.status = decision
    return_request.reviewed_by = reviewer.id
    return_request.reviewed_at = datetime.now(timezone.utc)
    return_request.review_comment = comment.strip() if comment else None

    if decision == ReturnRequestStatus.APPROVED:
        restock_return_items(db, order_id=return_request.order_id)

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


def advance_return_status(
    db: Session,
    *,
    return_request: ReturnRequest,
    changed_by: User,
    target_status: ReturnRequestStatus,
    comment: str | None = None,
) -> ReturnRequest:
    """Move an already-reviewed return request further through its
    post-approval lifecycle (approved -> returned -> refunded)."""

    validate_return_status_transition(return_request.status, target_status)

    previous_status = return_request.status
    return_request.status = target_status

    record_return_request_history(
        db,
        return_request=return_request,
        previous_status=previous_status,
        new_status=target_status,
        changed_by=changed_by.id,
        comment=comment.strip() if comment else None,
    )

    db.commit()
    db.refresh(return_request)
    return return_request


def process_return_refund(
    db: Session,
    *,
    return_request: ReturnRequest,
    changed_by: User,
    comment: str | None = None,
) -> ReturnRequest:
    """Issue a real Stripe refund for the return's order and move the return
    request to 'refunded'. Can be initiated as soon as the return is
    'approved' - if it hasn't been marked 'returned' yet, that step is
    recorded automatically first so the audit trail still shows both steps.
    Also callable directly from 'returned'."""

    if return_request.status not in (
        ReturnRequestStatus.APPROVED,
        ReturnRequestStatus.RETURNED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot refund a return request that is '{return_request.status.value}'. "
                "It must be approved or returned first."
            ),
        )

    order = return_request.order
    payment = get_payment_by_order_id(db, order.id)
    if not payment or payment.status != PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order has no completed payment to refund.",
        )

    if return_request.status == ReturnRequestStatus.APPROVED:
        return_request = advance_return_status(
            db,
            return_request=return_request,
            changed_by=changed_by,
            target_status=ReturnRequestStatus.RETURNED,
            comment="Marked returned automatically when the refund was initiated.",
        )

    try:
        stripe = get_stripe_client()
        refund = stripe.Refund.create(payment_intent=payment.transaction_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to process the refund with Stripe",
        ) from exc

    payment.status = PaymentStatus.REFUNDED
    payment.stripe_refund_id = refund.id
    payment.refunded_at = datetime.now(timezone.utc)
    order.payment_status = PaymentStatus.REFUNDED.value

    return advance_return_status(
        db,
        return_request=return_request,
        changed_by=changed_by,
        target_status=ReturnRequestStatus.REFUNDED,
        comment=comment,
    )


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
