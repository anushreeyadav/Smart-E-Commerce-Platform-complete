from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.stripe_client import get_stripe_client, stripe_field
from app.db.database import SessionLocal
from app.services.notification_events import (
    handle_stripe_payment_failed,
    handle_stripe_payment_succeeded,
)
from app.services.order_service import (
    get_order_by_id,
    get_order_by_payment_intent_id,
)


router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    stripe = get_stripe_client()

    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")
    webhook_secret = request.app.state.stripe_webhook_secret

    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret is not configured",
        )

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature header",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=webhook_secret,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe payload",
        ) from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature",
        ) from exc

    event_type = event["type"]
    data_object = event["data"]["object"]
    metadata = stripe_field(data_object, "metadata") or {}
    payment_intent_id = (
        stripe_field(data_object, "payment_intent")
        or stripe_field(data_object, "id")
    )
    order_id = stripe_field(metadata, "order_id")

    db: Session = SessionLocal()

    try:
        order = None

        if order_id:
            order = get_order_by_id(db, order_id)

        if not order and payment_intent_id:
            order = get_order_by_payment_intent_id(
                db,
                payment_intent_id,
            )

        if not order:
            return {
                "received": True,
                "ignored": True,
            }

        if event_type in {
            "checkout.session.completed",
            "payment_intent.succeeded",
        }:
            payment = await handle_stripe_payment_succeeded(
                db,
                order=order,
                payment_intent_id=payment_intent_id,
                background_tasks=background_tasks,
            )

            return {
                "received": True,
                "order_id": order.id,
                "payment_id": payment.id,
                "status": payment.status.value,
            }

        if event_type in {
            "checkout.session.async_payment_failed",
            "payment_intent.payment_failed",
            "checkout.session.expired",
            "payment_intent.canceled",
        }:
            payment = await handle_stripe_payment_failed(
                db,
                order=order,
                payment_intent_id=payment_intent_id,
                background_tasks=background_tasks,
            )

            return {
                "received": True,
                "order_id": order.id,
                "payment_id": payment.id,
                "status": payment.status.value,
            }

        return {
            "received": True,
            "ignored": True,
            "event": event_type,
        }
    finally:
        db.close()
