from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.order import OrderResponse, OrderStatusUpdate
from app.services.notification_events import handle_order_status_change
from app.services.order_service import (
    build_order_response,
    get_order_by_id,
    get_order_items,
    list_orders,
    list_orders_for_user,
)


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.get("", response_model=list[OrderResponse])
def list_all_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    orders = list_orders(db)
    return [
        build_order_response(order, get_order_items(db, order.id))
        for order in orders
    ]


@router.get("/me", response_model=list[OrderResponse])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orders = list_orders_for_user(db, current_user.id)
    return [
        build_order_response(order, get_order_items(db, order.id))
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

    return build_order_response(order, get_order_items(db, order.id))


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
    )

    return build_order_response(
        updated_order,
        get_order_items(db, updated_order.id),
    )
