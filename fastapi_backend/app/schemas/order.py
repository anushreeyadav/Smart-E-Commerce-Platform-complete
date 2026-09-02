from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.order import OrderStatus
from app.models.return_request import ReturnRequestStatus
from app.models.payment import PaymentStatus
from app.schemas.payment import PaymentResponse


class CheckoutRequest(BaseModel):
    payment_method: str = Field(
        default="stripe",
        min_length=2,
        max_length=50,
    )
    currency: str = Field(
        default="inr",
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
    shipping_address: Optional[str] = Field(
        default=None,
        max_length=1000,
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


class ReturnRequestCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    comment: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Return reason cannot be blank")
        return value


class ReturnRequestHistoryEntry(BaseModel):
    id: str
    previous_status: Optional[str] = None
    new_status: str
    comment: Optional[str] = None
    changed_by: Optional[str] = None
    changed_by_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReturnRequestResponse(BaseModel):
    id: str
    order_id: str
    user_id: str
    reason: str
    comments: Optional[str] = None
    status: ReturnRequestStatus
    created_at: datetime
    updated_at: datetime
    reviewed_by: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    history: List[ReturnRequestHistoryEntry] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ReturnApproveRequest(BaseModel):
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReturnRejectRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=2000)

    @field_validator("comment")
    @classmethod
    def comment_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A reason is required to reject a return request")
        return value


class ReturnTransitionRequest(BaseModel):
    comment: Optional[str] = Field(default=None, max_length=2000)


class PaginatedReturnRequestsResponse(BaseModel):
    items: List[ReturnRequestResponse]
    total: int
    page: int
    page_size: int


class OrderStatusHistoryEntry(BaseModel):
    id: str
    previous_status: Optional[str] = None
    new_status: str
    changed_by: Optional[str] = None
    changed_by_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: str
    user_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    status: OrderStatus
    payment_status: PaymentStatus
    total_amount: Decimal
    payment_method: str
    currency: str
    stripe_checkout_session_id: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    shipping_address: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    items: List[OrderItemResponse] = Field(default_factory=list)
    return_request: Optional[ReturnRequestResponse] = None
    return_eligible: bool = False
    return_window_expires_at: Optional[datetime] = None
    status_history: List[OrderStatusHistoryEntry] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PaginatedOrdersResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int


class CheckoutResponse(BaseModel):
    message: str
    order: OrderResponse
    payment: PaymentResponse
    checkout_session_id: Optional[str] = None
    checkout_session_url: Optional[str] = None
    payment_intent_id: Optional[str] = None
    payment_intent_client_secret: Optional[str] = None
