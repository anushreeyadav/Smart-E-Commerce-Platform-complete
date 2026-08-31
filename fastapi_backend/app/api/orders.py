from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.order import OrderStatus
from app.models.return_request import ReturnRequest, ReturnRequestStatus
from app.schemas.order import (
    OrderResponse,
    OrderStatusUpdate,
    PaginatedOrdersResponse,
    ReturnApproveRequest,
    ReturnRejectRequest,
    ReturnRequestCreate,
    ReturnRequestResponse,
)
from app.services.notification_events import handle_order_status_change, notify_user
from app.models.notification import NotificationType
from app.services.order_service import (
    build_order_response,
    get_order_by_id,
    get_order_items,
    list_orders_filtered,
    list_orders_for_user,
    record_order_status_history,
    validate_transition,
)
from app.services.return_service import (
    get_return_request_for_order,
    is_return_eligible,
    record_return_request_history,
    return_window_expires_at,
    review_return_request,
    validate_return_request,
)


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


def _order_response(db: Session, order):
    response = build_order_response(order, get_order_items(db, order.id), include_history=True)
    response["return_request"] = get_return_request_for_order(db, order.id)
    response["return_eligible"] = is_return_eligible(order)
    response["return_window_expires_at"] = return_window_expires_at(order)
    return response


@router.get("", response_model=PaginatedOrdersResponse)
def list_all_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
    status_filter: Optional[OrderStatus] = Query(default=None, alias="status"),
    payment_status: Optional[str] = Query(default=None),
    return_status: Optional[str] = Query(
        default=None,
        description="pending | approved | rejected | none",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Matches order id, customer name, or customer email",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    orders, total = list_orders_filtered(
        db,
        order_status=status_filter,
        payment_status=payment_status,
        return_status=return_status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [_order_response(db, order) for order in orders],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/me", response_model=list[OrderResponse])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orders = list_orders_for_user(db, current_user.id)
    return [
        _order_response(db, order)
        for order in orders
    ]


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = get_order_by_id(db, order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own orders",
        )

    return _order_response(db, order)


@router.post("/{order_id}/return", response_model=ReturnRequestResponse, status_code=status.HTTP_201_CREATED)
def create_return_request(
    order_id: str,
    request: ReturnRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only request returns for your own orders")

    if get_return_request_for_order(db, order.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A return request already exists for this order")
    validate_return_request(order)
    validate_transition(order.status, OrderStatus.RETURN_REQUESTED)

    return_request = ReturnRequest(
        order_id=order.id,
        user_id=current_user.id,
        reason=request.reason.strip(),
        comments=request.comment.strip() if request.comment else None,
        status=ReturnRequestStatus.PENDING,
    )
    db.add(return_request)
    try:
        # Flush first: an order is not moved to return_requested if inserting
        # the return request fails (including a concurrent duplicate request).
        db.flush()
        record_return_request_history(
            db,
            return_request=return_request,
            previous_status=None,
            new_status=ReturnRequestStatus.PENDING,
            changed_by=current_user.id,
        )
        previous_order_status = order.status
        order.status = OrderStatus.RETURN_REQUESTED
        record_order_status_history(
            db,
            order=order,
            previous_status=previous_order_status,
            new_status=OrderStatus.RETURN_REQUESTED,
            changed_by=current_user.id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A return request already exists for this order")
    db.refresh(return_request)
    return return_request


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def change_order_status(
    order_id: str,
    request: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    order = get_order_by_id(db, order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    updated_order, _changed = await handle_order_status_change(
        db,
        order=order,
        new_status=request.status,
        background_tasks=background_tasks,
        changed_by_user_id=current_user.id,
    )

    return _order_response(db, updated_order)


def _get_return_request_or_404(db: Session, order_id: str) -> ReturnRequest:
    order = get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return_request = get_return_request_for_order(db, order_id)
    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No return request exists for this order",
        )
    return return_request


@router.post(
    "/{order_id}/return/approve",
    response_model=ReturnRequestResponse,
)
async def approve_return(
    order_id: str,
    request: ReturnApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    return_request = _get_return_request_or_404(db, order_id)

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

    return updated


@router.post(
    "/{order_id}/return/reject",
    response_model=ReturnRequestResponse,
)
async def reject_return(
    order_id: str,
    request: ReturnRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    return_request = _get_return_request_or_404(db, order_id)

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

    return updated
