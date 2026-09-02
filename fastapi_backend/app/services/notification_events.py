from __future__ import annotations

from datetime import datetime, timezone

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.services import order_service
from app.services.connection_manager import manager
from app.services.email_service import (
    queue_templated_email,
    send_order_confirmation_email,
    send_order_delivered_email,
    send_order_shipped_email,
    send_payment_failed_email,
    send_payment_success_email,
)
from app.services.notification_service import create_notification


def _serialize_notification(notification: Notification) -> dict:
    return {
        "id": notification.id,
        "type": notification.type.value,
        "message": notification.message,
        "read_status": notification.read_status,
        "timestamp": notification.timestamp.isoformat(),
    }


async def notify_user(
    db: Session,
    *,
    user: User,
    notification_type: NotificationType,
    message: str,
) -> Notification:
    notification = create_notification(
        db,
        user_id=user.id,
        notification_type=notification_type,
        message=message,
    )

    await manager.send_to_user(
        user.id,
        "notification_created",
        _serialize_notification(notification),
    )

    return notification


async def emit_order_status_updated(
    *,
    user: User,
    order: Order,
    old_status: OrderStatus,
    message: str,
) -> None:
    await manager.send_to_user(
        user.id,
        "order_status_updated",
        {
            "order_id": order.id,
            "old_status": old_status.value,
            "new_status": order.status.value,
            "payment_status": order.payment_status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def _get_user(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


async def handle_order_created(
    db: Session,
    *,
    user: User,
    order: Order,
    background_tasks: BackgroundTasks,
) -> Notification:
    notification = await notify_user(
        db,
        user=user,
        notification_type=NotificationType.ORDER_CONFIRMED,
        message=f"Your order {order.id} has been confirmed.",
    )

    queue_templated_email(
        background_tasks,
        send_order_confirmation_email,
        user,
        order,
    )

    return notification


async def _emit_payment_success(
    db: Session,
    *,
    order: Order,
    old_status: OrderStatus,
    payment: Payment,
    background_tasks: BackgroundTasks,
) -> None:
    user = _get_user(db, order.user_id)

    if not user:
        return

    message = f"Payment successful for order {order.id}."

    await notify_user(
        db,
        user=user,
        notification_type=NotificationType.PAYMENT_SUCCESS,
        message=message,
    )

    await emit_order_status_updated(
        user=user,
        order=order,
        old_status=old_status,
        message=message,
    )

    queue_templated_email(
        background_tasks,
        send_payment_success_email,
        user,
        order,
        payment,
    )


async def _emit_payment_failed(
    db: Session,
    *,
    order: Order,
    background_tasks: BackgroundTasks,
) -> None:
    user = _get_user(db, order.user_id)

    if not user:
        return

    message = f"Payment failed for order {order.id}. Please try again."

    await notify_user(
        db,
        user=user,
        notification_type=NotificationType.PAYMENT_FAILED,
        message=message,
    )

    await emit_order_status_updated(
        user=user,
        order=order,
        old_status=order.status,
        message=message,
    )

    queue_templated_email(
        background_tasks,
        send_payment_failed_email,
        user,
        order,
    )


async def handle_stripe_payment_succeeded(
    db: Session,
    *,
    order: Order,
    payment_intent_id: str | None,
    background_tasks: BackgroundTasks,
) -> Payment:
    old_status = order.status

    payment, changed = order_service.mark_stripe_payment_paid(
        db,
        order=order,
        payment_intent_id=payment_intent_id,
    )

    if changed:
        await _emit_payment_success(
            db,
            order=order,
            old_status=old_status,
            payment=payment,
            background_tasks=background_tasks,
        )

    return payment


async def handle_stripe_payment_failed(
    db: Session,
    *,
    order: Order,
    payment_intent_id: str | None,
    background_tasks: BackgroundTasks,
) -> Payment:
    payment, changed = order_service.mark_stripe_payment_failed(
        db,
        order=order,
        payment_intent_id=payment_intent_id,
    )

    if changed:
        await _emit_payment_failed(db, order=order, background_tasks=background_tasks)

    return payment


async def handle_stripe_payment_sync(
    db: Session,
    *,
    order: Order,
    background_tasks: BackgroundTasks,
) -> tuple[Payment, str]:
    """Synchronous fallback for right after a customer returns from Stripe
    Checkout: verifies the real payment state directly with Stripe and, if
    it has resolved, applies the exact same transition the async webhook
    would (reusing handle_stripe_payment_succeeded/failed below - no
    duplicated business logic). Safe to call repeatedly or race against the
    webhook, since both paths funnel through the same idempotent functions.
    """

    verified_state, payment_intent_id = order_service.verify_stripe_checkout_payment(
        db, order=order
    )

    if verified_state == "paid":
        payment = await handle_stripe_payment_succeeded(
            db,
            order=order,
            payment_intent_id=payment_intent_id,
            background_tasks=background_tasks,
        )
        return payment, verified_state

    if verified_state == "failed":
        payment = await handle_stripe_payment_failed(
            db,
            order=order,
            payment_intent_id=payment_intent_id,
            background_tasks=background_tasks,
        )
        return payment, verified_state

    payment = order_service.get_payment_by_order_id(db, order.id)

    if not payment:
        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            payment_method="stripe",
            status=PaymentStatus.PENDING,
            transaction_id=payment_intent_id,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

    return payment, verified_state


async def handle_manual_payment_confirmed(
    db: Session,
    *,
    order: Order,
    provider: str,
    transaction_id: str | None,
    background_tasks: BackgroundTasks,
) -> Payment:
    old_status = order.status

    payment, changed = order_service.confirm_payment(
        db,
        order,
        provider=provider,
        transaction_id=transaction_id,
    )

    if changed:
        await _emit_payment_success(
            db,
            order=order,
            old_status=old_status,
            payment=payment,
            background_tasks=background_tasks,
        )

    return payment


_STATUS_NOTIFICATION_MAP: dict[OrderStatus, NotificationType] = {
    OrderStatus.SHIPPED: NotificationType.ORDER_SHIPPED,
    OrderStatus.DELIVERED: NotificationType.ORDER_DELIVERED,
}

_STATUS_EMAIL_MAP = {
    OrderStatus.SHIPPED: send_order_shipped_email,
    OrderStatus.DELIVERED: send_order_delivered_email,
}


async def handle_order_status_change(
    db: Session,
    *,
    order: Order,
    new_status: OrderStatus,
    background_tasks: BackgroundTasks,
    changed_by_user_id: str | None = None,
) -> tuple[Order, bool]:
    old_status = order.status

    order, changed = order_service.update_order_status(
        db, order, new_status, changed_by=changed_by_user_id
    )

    if not changed:
        return order, False

    user = _get_user(db, order.user_id)
    notification_type = _STATUS_NOTIFICATION_MAP.get(new_status)

    message = f"Your order {order.id} status is now {new_status.value.replace('_', ' ')}."

    if user and notification_type:
        message = (
            f"Your order {order.id} has been shipped."
            if new_status == OrderStatus.SHIPPED
            else f"Your order {order.id} has been delivered."
        )

        await notify_user(
            db,
            user=user,
            notification_type=notification_type,
            message=message,
        )

        email_fn = _STATUS_EMAIL_MAP.get(new_status)

        if email_fn:
            queue_templated_email(background_tasks, email_fn, user, order)

    if user:
        await emit_order_status_updated(
            user=user,
            order=order,
            old_status=old_status,
            message=message,
        )

    return order, True
