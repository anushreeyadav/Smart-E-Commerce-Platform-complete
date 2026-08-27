from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.stripe_client import get_frontend_url, get_stripe_client
from app.models.cart import Cart
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.product import Product
from app.models.user import User


MONEY_QUANTIZER = Decimal("0.01")

ALLOWED_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def validate_transition(
    current_status: OrderStatus,
    target_status: OrderStatus,
) -> None:
    if current_status == target_status:
        return

    if target_status not in ALLOWED_STATUS_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot move an order from '{current_status.value}' "
                f"to '{target_status.value}'."
            ),
        )


def _money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)


def _amount_to_cents(value: Decimal) -> int:
    return int((_money(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def build_order_response(order: Order, items: list[dict]) -> dict:
    return {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "payment_status": order.payment_status,
        "total_amount": order.total_amount,
        "payment_method": order.payment_method,
        "currency": order.currency,
        "stripe_checkout_session_id": order.stripe_checkout_session_id,
        "stripe_payment_intent_id": order.stripe_payment_intent_id,
        "created_at": order.created_at,
        "items": items,
    }


def get_order_items(db: Session, order_id: str) -> list[dict]:
    rows = (
        db.query(OrderItem, Product)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(OrderItem.order_id == order_id)
        .all()
    )

    items: list[dict] = []

    for order_item, product in rows:
        items.append(
            {
                "id": order_item.id,
                "product_id": order_item.product_id,
                "quantity": order_item.quantity,
                "unit_price": order_item.unit_price,
                "product_name": product.name if product else None,
            }
        )

    return items


def get_order_by_id(db: Session, order_id: str) -> Order | None:
    return db.query(Order).filter(Order.id == order_id).first()


def get_payment_by_order_id(db: Session, order_id: str) -> Payment | None:
    return db.query(Payment).filter(Payment.order_id == order_id).first()


def get_order_by_payment_intent_id(db: Session, payment_intent_id: str) -> Order | None:
    return (
        db.query(Order)
        .filter(Order.stripe_payment_intent_id == payment_intent_id)
        .first()
    )


def list_orders(db: Session) -> list[Order]:
    return db.query(Order).order_by(Order.created_at.desc()).all()


def list_orders_for_user(db: Session, user_id: str) -> list[Order]:
    return (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )


def create_order_from_cart(
    db: Session,
    user: User,
    *,
    payment_method: str = "stripe",
    currency: str = "usd",
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> tuple[Order, Payment, dict]:
    cart_items = db.query(Cart).filter(Cart.user_id == user.id).all()

    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    normalized_currency = currency.strip().lower() or "usd"
    order_total = Decimal("0.00")
    resolved_items: list[tuple[Cart, Product, Decimal]] = []

    for cart_item in cart_items:
        product = (
            db.query(Product)
            .filter(Product.id == cart_item.product_id)
            .first()
        )

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product is unavailable: {product.name}",
            )

        if product.stock < cart_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough stock for {product.name}",
            )

        unit_price = _money(product.price)
        order_total += unit_price * cart_item.quantity
        resolved_items.append((cart_item, product, unit_price))

    order = Order(
        user_id=user.id,
        status=OrderStatus.CONFIRMED,
        payment_status=PaymentStatus.PENDING.value,
        total_amount=_money(order_total),
        payment_method=payment_method,
        currency=normalized_currency,
    )

    db.add(order)
    db.flush()

    for cart_item, product, unit_price in resolved_items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=cart_item.quantity,
                unit_price=unit_price,
            )
        )

        product.stock -= cart_item.quantity
        db.delete(cart_item)

    frontend_url = get_frontend_url()
    resolved_success_url = (
        success_url
        or f"{frontend_url}/cart?checkout=success&order_id={order.id}"
    )
    resolved_cancel_url = (
        cancel_url
        or f"{frontend_url}/cart?checkout=cancelled&order_id={order.id}"
    )

    try:
        stripe = get_stripe_client()
        payment_intent = stripe.PaymentIntent.create(
            amount=_amount_to_cents(order.total_amount),
            currency=normalized_currency,
            automatic_payment_methods={"enabled": True},
            metadata={
                "order_id": order.id,
                "user_id": user.id,
            },
        )

        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": normalized_currency,
                        "product_data": {
                            "name": f"Smart E-Commerce Order {order.id}",
                        },
                        "unit_amount": _amount_to_cents(order.total_amount),
                    },
                    "quantity": 1,
                }
            ],
            success_url=resolved_success_url,
            cancel_url=resolved_cancel_url,
            metadata={
                "order_id": order.id,
                "payment_intent_id": payment_intent.id,
                "user_id": user.id,
            },
            payment_intent_data={
                "metadata": {
                    "order_id": order.id,
                    "user_id": user.id,
                }
            },
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to initialize Stripe checkout",
        ) from exc

    payment = Payment(
        order_id=order.id,
        amount=order.total_amount,
        payment_method=payment_method,
        status=PaymentStatus.PENDING,
        transaction_id=payment_intent.id,
    )

    order.stripe_payment_intent_id = payment_intent.id
    order.stripe_checkout_session_id = checkout_session.id
    payment.payment_method = payment_method

    db.add(payment)
    db.commit()
    db.refresh(order)
    db.refresh(payment)

    return (
        order,
        payment,
        {
            "checkout_session_id": checkout_session.id,
            "checkout_session_url": checkout_session.url,
            "payment_intent_id": payment_intent.id,
            "payment_intent_client_secret": payment_intent.client_secret,
        },
    )


def update_order_status(
    db: Session,
    order: Order,
    status_value: OrderStatus,
    *,
    enforce_transition: bool = True,
) -> tuple[Order, bool]:
    if enforce_transition:
        validate_transition(order.status, status_value)

    if order.status == status_value:
        return order, False

    order.status = status_value
    db.commit()
    db.refresh(order)
    return order, True


def confirm_payment(
    db: Session,
    order: Order,
    *,
    provider: str = "stripe",
    transaction_id: str | None = None,
) -> tuple[Payment, bool]:
    payment = get_payment_by_order_id(db, order.id)

    if not payment:
        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            payment_method=provider,
            status=PaymentStatus.PENDING,
            transaction_id=transaction_id,
        )
        db.add(payment)
        db.flush()

    if payment.status == PaymentStatus.PAID and order.payment_status == PaymentStatus.PAID.value:
        return payment, False

    payment.payment_method = provider
    payment.transaction_id = transaction_id or payment.transaction_id
    payment.status = PaymentStatus.PAID
    payment.paid_at = datetime.now(timezone.utc)

    order.payment_status = PaymentStatus.PAID.value
    order.payment_method = provider
    if order.status in ALLOWED_STATUS_TRANSITIONS and OrderStatus.PAID in ALLOWED_STATUS_TRANSITIONS[order.status]:
        order.status = OrderStatus.PAID
    order.stripe_payment_intent_id = payment.transaction_id or order.stripe_payment_intent_id

    db.commit()
    db.refresh(payment)
    db.refresh(order)

    return payment, True


def mark_stripe_payment_paid(
    db: Session,
    *,
    order: Order,
    payment_intent_id: str | None = None,
) -> tuple[Payment, bool]:
    payment = get_payment_by_order_id(db, order.id)

    if not payment:
        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            payment_method="stripe",
            status=PaymentStatus.PENDING,
            transaction_id=payment_intent_id,
        )
        db.add(payment)
        db.flush()

    if payment.status == PaymentStatus.PAID and order.payment_status == PaymentStatus.PAID.value:
        return payment, False

    payment.payment_method = "stripe"
    payment.transaction_id = payment_intent_id or payment.transaction_id
    payment.status = PaymentStatus.PAID
    payment.paid_at = datetime.now(timezone.utc)

    order.payment_status = PaymentStatus.PAID.value
    order.payment_method = "stripe"
    if order.status in ALLOWED_STATUS_TRANSITIONS and OrderStatus.PAID in ALLOWED_STATUS_TRANSITIONS[order.status]:
        order.status = OrderStatus.PAID
    if payment_intent_id:
        order.stripe_payment_intent_id = payment_intent_id

    db.commit()
    db.refresh(payment)
    db.refresh(order)
    return payment, True


def mark_stripe_payment_failed(
    db: Session,
    *,
    order: Order,
    payment_intent_id: str | None = None,
) -> tuple[Payment, bool]:
    payment = get_payment_by_order_id(db, order.id)

    if not payment:
        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            payment_method="stripe",
            status=PaymentStatus.FAILED,
            transaction_id=payment_intent_id,
        )
        db.add(payment)
    else:
        if payment.status == PaymentStatus.FAILED and order.payment_status == PaymentStatus.FAILED.value:
            return payment, False

        payment.payment_method = "stripe"
        payment.transaction_id = (
            payment_intent_id or payment.transaction_id
        )
        payment.status = PaymentStatus.FAILED

    order.payment_status = PaymentStatus.FAILED.value

    if payment_intent_id:
        order.stripe_payment_intent_id = payment_intent_id

    db.commit()
    db.refresh(payment)
    db.refresh(order)

    return payment, True
