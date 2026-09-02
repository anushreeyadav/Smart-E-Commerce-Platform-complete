from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.stripe_client import get_frontend_url, get_stripe_client, stripe_field
from app.models.cart import Cart
from app.models.order import Order, OrderItem, OrderStatus
from app.models.order_status_history import OrderStatusHistory
from app.models.payment import Payment, PaymentStatus
from app.models.product import Product
from app.models.return_request import ReturnRequest, ReturnRequestStatus
from app.models.user import User
from app.services.pricing_service import convert_from_base, normalize_currency


MONEY_QUANTIZER = Decimal("0.01")

ALLOWED_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    # OUT_FOR_DELIVERY is an optional intermediate step: SHIPPED -> DELIVERED
    # directly is still allowed so the existing flow keeps working.
    OrderStatus.SHIPPED: {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: {OrderStatus.RETURN_REQUESTED},
    OrderStatus.RETURN_REQUESTED: set(),
    OrderStatus.CANCELLED: set(),
}


def record_order_status_history(
    db: Session,
    *,
    order: Order,
    previous_status: OrderStatus | None,
    new_status: OrderStatus,
    changed_by: str | None,
) -> None:
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            previous_status=previous_status.value if previous_status else None,
            new_status=new_status.value,
            changed_by=changed_by,
        )
    )


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


def build_order_response(
    order: Order,
    items: list[dict],
    *,
    include_history: bool = False,
) -> dict:
    response = {
        "id": order.id,
        "user_id": order.user_id,
        "customer_name": order.user.name if order.user else None,
        "customer_email": order.user.email if order.user else None,
        "status": order.status,
        "payment_status": order.payment_status,
        "total_amount": order.total_amount,
        "payment_method": order.payment_method,
        "currency": order.currency,
        "stripe_checkout_session_id": order.stripe_checkout_session_id,
        "stripe_payment_intent_id": order.stripe_payment_intent_id,
        "shipping_address": order.shipping_address,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "delivered_at": order.delivered_at,
        "items": items,
    }

    if include_history:
        response["status_history"] = [
            {
                "id": entry.id,
                "previous_status": entry.previous_status,
                "new_status": entry.new_status,
                "changed_by": entry.changed_by,
                "changed_by_name": entry.changed_by_user.name if entry.changed_by_user else None,
                "created_at": entry.created_at,
            }
            for entry in order.status_history
        ]

    return response


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


def list_orders_filtered(
    db: Session,
    *,
    order_status: OrderStatus | None = None,
    payment_status: str | None = None,
    return_status: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Order], int]:
    query = (
        db.query(Order)
        .options(joinedload(Order.user))
        .join(User, User.id == Order.user_id)
    )

    if order_status:
        query = query.filter(Order.status == order_status)

    if payment_status:
        query = query.filter(Order.payment_status == payment_status.strip().lower())

    if return_status:
        normalized_return_status = return_status.strip().lower()
        if normalized_return_status == "none":
            query = query.filter(~Order.return_request.has())
        else:
            try:
                status_value = ReturnRequestStatus(normalized_return_status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown return status '{return_status}'.",
                )
            query = query.filter(
                Order.return_request.has(ReturnRequest.status == status_value)
            )

    if search:
        like_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Order.id.ilike(like_pattern),
                User.name.ilike(like_pattern),
                User.email.ilike(like_pattern),
            )
        )

    total = query.count()

    orders = (
        query.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return orders, total


def list_orders_for_user(db: Session, user_id: str) -> list[Order]:
    return (
        db.query(Order)
        .options(joinedload(Order.user))
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )


def create_order_from_cart(
    db: Session,
    user: User,
    *,
    payment_method: str = "stripe",
    currency: str = "inr",
    success_url: str | None = None,
    cancel_url: str | None = None,
    shipping_address: str | None = None,
) -> tuple[Order, Payment, dict]:
    cart_items = db.query(Cart).filter(Cart.user_id == user.id).all()

    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    normalized_currency = normalize_currency(currency)
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

        unit_price = convert_from_base(_money(product.price), normalized_currency)
        order_total += unit_price * cart_item.quantity
        resolved_items.append((cart_item, product, unit_price))

    order = Order(
        user_id=user.id,
        status=OrderStatus.CONFIRMED,
        payment_status=PaymentStatus.PENDING.value,
        total_amount=_money(order_total),
        payment_method=payment_method,
        currency=normalized_currency,
        shipping_address=shipping_address.strip() if shipping_address else None,
    )

    db.add(order)
    db.flush()

    record_order_status_history(
        db,
        order=order,
        previous_status=None,
        new_status=OrderStatus.CONFIRMED,
        changed_by=None,
    )

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
    changed_by: str | None = None,
) -> tuple[Order, bool]:
    if enforce_transition:
        validate_transition(order.status, status_value)

    if order.status == status_value:
        return order, False

    previous_status = order.status
    order.status = status_value
    if status_value == OrderStatus.DELIVERED:
        order.delivered_at = datetime.now(timezone.utc)
    record_order_status_history(
        db,
        order=order,
        previous_status=previous_status,
        new_status=status_value,
        changed_by=changed_by,
    )
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
        previous_status = order.status
        order.status = OrderStatus.PAID
        record_order_status_history(
            db,
            order=order,
            previous_status=previous_status,
            new_status=OrderStatus.PAID,
            changed_by=None,
        )
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
        previous_status = order.status
        order.status = OrderStatus.PAID
        record_order_status_history(
            db,
            order=order,
            previous_status=previous_status,
            new_status=OrderStatus.PAID,
            changed_by=None,
        )
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


def verify_stripe_checkout_payment(
    db: Session,
    *,
    order: Order,
) -> tuple[str, str | None]:
    """Ask Stripe directly what happened to this order's Checkout Session,
    rather than trusting the client. This is the source-of-truth check used
    as a synchronous fallback right after a customer returns from Stripe
    Checkout, for cases where the async webhook hasn't (yet) arrived.

    Returns (verified_state, payment_intent_id) where verified_state is one
    of "paid", "failed", "pending", or "already_settled". This function only
    reads from Stripe - callers apply the actual transition (reusing the
    same mark_stripe_payment_paid/failed the webhook uses), so verifying
    never risks double-applying a state change.
    """

    payment = get_payment_by_order_id(db, order.id)

    if payment and payment.status in (PaymentStatus.PAID, PaymentStatus.REFUNDED):
        return "already_settled", payment.transaction_id

    if not order.stripe_checkout_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order was not paid through Stripe Checkout.",
        )

    stripe = get_stripe_client()

    try:
        session = stripe.checkout.Session.retrieve(order.stripe_checkout_session_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to verify payment status with Stripe",
        ) from exc

    payment_intent_id = stripe_field(session, "payment_intent") or order.stripe_payment_intent_id

    if stripe_field(session, "payment_status") == "paid":
        return "paid", payment_intent_id

    if stripe_field(session, "status") == "expired":
        return "failed", payment_intent_id

    return "pending", payment_intent_id
