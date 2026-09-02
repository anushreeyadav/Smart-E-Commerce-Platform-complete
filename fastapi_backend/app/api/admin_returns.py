from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.notification import NotificationType
from app.models.return_request import ReturnRequest, ReturnRequestStatus
from app.models.user import User, UserRole
from app.schemas.order import (
    PaginatedReturnRequestsResponse,
    ReturnApproveRequest,
    ReturnRejectRequest,
    ReturnRequestResponse,
    ReturnTransitionRequest,
)
from app.services.email_service import (
    queue_templated_email,
    send_refund_processed_email,
    send_return_approved_email,
    send_return_rejected_email,
)
from app.services.notification_events import notify_user
from app.services.return_service import (
    advance_return_status,
    get_return_request_by_id,
    list_return_requests_filtered,
    process_return_refund,
    review_return_request,
)


router = APIRouter(
    prefix="/admin/returns",
    tags=["Admin - Returns"],
)


def _get_return_request_or_404(db: Session, return_id: str) -> ReturnRequest:
    return_request = get_return_request_by_id(db, return_id)
    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )
    return return_request


@router.get("", response_model=PaginatedReturnRequestsResponse)
def list_returns(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
    status_filter: Optional[ReturnRequestStatus] = Query(default=None, alias="status"),
    search: Optional[str] = Query(
        default=None,
        description="Matches return request id, order id, customer name, or customer email",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    items, total = list_return_requests_filtered(
        db,
        status_filter=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{return_id}/approve", response_model=ReturnRequestResponse)
async def approve_return_request(
    return_id: str,
    request: ReturnApproveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    return_request = _get_return_request_or_404(db, return_id)

    # review_return_request commits the approval (and the resulting restock)
    # before returning, so notifications below only fire once that has
    # actually succeeded.
    updated = review_return_request(
        db,
        return_request=return_request,
        reviewer=current_user,
        decision=ReturnRequestStatus.APPROVED,
        comment=request.comment,
    )

    await notify_user(
        db,
        user=updated.user,
        notification_type=NotificationType.RETURN_APPROVED,
        message=f"Your return request for order {updated.order_id} has been approved.",
    )
    queue_templated_email(background_tasks, send_return_approved_email, updated.user, updated)

    return updated


@router.post("/{return_id}/reject", response_model=ReturnRequestResponse)
async def reject_return_request(
    return_id: str,
    request: ReturnRejectRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    return_request = _get_return_request_or_404(db, return_id)

    updated = review_return_request(
        db,
        return_request=return_request,
        reviewer=current_user,
        decision=ReturnRequestStatus.REJECTED,
        comment=request.comment,
    )

    await notify_user(
        db,
        user=updated.user,
        notification_type=NotificationType.RETURN_REJECTED,
        message=f"Your return request for order {updated.order_id} was rejected: {request.comment}",
    )
    queue_templated_email(background_tasks, send_return_rejected_email, updated.user, updated)

    return updated


@router.post("/{return_id}/mark-returned", response_model=ReturnRequestResponse)
def mark_return_as_returned(
    return_id: str,
    request: ReturnTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    return_request = _get_return_request_or_404(db, return_id)

    return advance_return_status(
        db,
        return_request=return_request,
        changed_by=current_user,
        target_status=ReturnRequestStatus.RETURNED,
        comment=request.comment,
    )


@router.post("/{return_id}/refund", response_model=ReturnRequestResponse)
async def refund_return_request(
    return_id: str,
    request: ReturnTransitionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    """Initiate the refund for an approved (or already-returned) return
    request: issues a real Stripe refund for the order's payment and moves
    the return to 'refunded'. Callable directly once approved - if the item
    hasn't been marked returned yet, that step is recorded automatically."""

    return_request = _get_return_request_or_404(db, return_id)

    # process_return_refund only mutates payment/order/return state once the
    # Stripe refund call has actually succeeded (a Stripe failure raises
    # before any of that is touched) - so reaching here means the refund is
    # real, and only then do we tell the customer about it.
    updated = process_return_refund(
        db,
        return_request=return_request,
        changed_by=current_user,
        comment=request.comment,
    )

    await notify_user(
        db,
        user=updated.user,
        notification_type=NotificationType.REFUND_PROCESSED,
        message=f"Your refund for order {updated.order_id} has been processed.",
    )
    queue_templated_email(background_tasks, send_refund_processed_email, updated.user, updated)

    return updated
