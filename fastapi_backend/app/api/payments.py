from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.order import Order
from app.models.payment import Payment
from app.models.user import User, UserRole
from app.schemas.payment import PaymentConfirmRequest, PaymentResponse
from app.services.notification_events import handle_manual_payment_confirmed
from app.services.order_service import (
    get_order_by_id,
    get_payment_by_order_id,
)


router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


@router.get("", response_model=list[PaymentResponse])
def list_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    payments = (
        db.query(Payment)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return payments


@router.get("/me", response_model=list[PaymentResponse])
def my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payments = (
        db.query(Payment)
        .join(Order, Order.id == Payment.order_id)
        .filter(Order.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return payments


@router.get("/{order_id}", response_model=PaymentResponse)
def get_payment(
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
            detail="You can only view your own payment",
        )

    payment = get_payment_by_order_id(db, order_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    return payment


@router.post("/{order_id}/confirm", response_model=PaymentResponse)
async def confirm_order_payment(
    order_id: str,
    request: PaymentConfirmRequest,
    background_tasks: BackgroundTasks,
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
            detail="You can only confirm your own payment",
        )

    return await handle_manual_payment_confirmed(
        db,
        order=order,
        provider=request.provider,
        transaction_id=request.transaction_id,
        background_tasks=background_tasks,
    )
