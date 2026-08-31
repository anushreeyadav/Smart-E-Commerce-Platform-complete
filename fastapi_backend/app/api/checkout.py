from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.config import BASE_CURRENCY, CURRENCY_RATES
from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.order import CheckoutRequest, CheckoutResponse
from app.services.notification_events import handle_order_created
from app.services.order_service import (
    build_order_response,
    create_order_from_cart,
    get_order_items,
)


router = APIRouter(
    tags=["Checkout"],
)


@router.get("/checkout/currencies")
def list_supported_currencies():
    return {
        "base_currency": BASE_CURRENCY,
        "currencies": [
            {"code": code, "rate_from_base": rate}
            for code, rate in CURRENCY_RATES.items()
        ],
    }


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def checkout(
    request: CheckoutRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CUSTOMER)),
):
    order, payment, stripe_session = create_order_from_cart(
        db,
        current_user,
        payment_method=request.payment_method,
        currency=request.currency,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        shipping_address=request.shipping_address,
    )

    await handle_order_created(
        db,
        user=current_user,
        order=order,
        background_tasks=background_tasks,
    )

    return {
        "message": "Checkout session created successfully",
        "order": build_order_response(
            order,
            get_order_items(db, order.id),
        ),
        "payment": payment,
        "checkout_session_id": stripe_session.get("checkout_session_id"),
        "checkout_session_url": stripe_session.get("checkout_session_url"),
        "payment_intent_id": stripe_session.get("payment_intent_id"),
        "payment_intent_client_secret": stripe_session.get(
            "payment_intent_client_secret"
        ),
    }