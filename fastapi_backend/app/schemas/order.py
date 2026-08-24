from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus
from app.models.payment import PaymentStatus
from app.schemas.payment import PaymentResponse


class CheckoutRequest(BaseModel):
    payment_method: str = Field(
        default="stripe",
        min_length=2,
        max_length=50,
    )
    currency: str = Field(
        default="usd",
        min_length=3,
        max_length=3,
    )
    success_url: Optional[str] = Field(
        default=None,
        max_length=500,
    )
    cancel_url: Optional[str] = Field(
        default=None,
        max_length=500,
    )


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    unit_price: Decimal
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: str
    user_id: str
    status: OrderStatus
    payment_status: PaymentStatus
    total_amount: Decimal
    payment_method: str
    currency: str
    stripe_checkout_session_id: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime
    items: List[OrderItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CheckoutResponse(BaseModel):
    message: str
    order: OrderResponse
    payment: PaymentResponse
    checkout_session_id: Optional[str] = None
    checkout_session_url: Optional[str] = None
    payment_intent_id: Optional[str] = None
    payment_intent_client_secret: Optional[str] = None
