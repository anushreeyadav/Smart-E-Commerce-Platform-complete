from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentStatus


class PaymentConfirmRequest(BaseModel):
    provider: str = Field(
        default="stripe",
        min_length=2,
        max_length=50,
    )

    transaction_id: Optional[str] = Field(
        default=None,
        max_length=120,
    )


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    amount: Decimal
    payment_method: str
    status: PaymentStatus
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    stripe_refund_id: Optional[str] = None
    refunded_at: Optional[datetime] = None
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentSyncResponse(BaseModel):
    payment: PaymentResponse
    verified_state: str
