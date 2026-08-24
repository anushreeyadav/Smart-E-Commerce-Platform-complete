from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductResponse


class CartAddRequest(BaseModel):
    product_id: str
    quantity: int = Field(
        default=1,
        ge=1,
    )


class CartUpdateRequest(BaseModel):
    product_id: str
    quantity: int = Field(
        ...,
        ge=1,
    )


class CartRemoveRequest(BaseModel):
    product_id: str


class CartItemResponse(BaseModel):
    id: str
    user_id: str
    product_id: str
    quantity: int
    unit_price: Decimal
    item_total: Decimal
    product: Optional[ProductResponse] = None

    model_config = ConfigDict(from_attributes=True)


class CartTotalsResponse(BaseModel):
    cart_total: Decimal
    tax_rate: Decimal = Decimal("0.00")
    tax: Decimal
    grand_total: Decimal
    total_items: int


class CartResponse(BaseModel):
    items: List[CartItemResponse] = Field(default_factory=list)
    totals: CartTotalsResponse


class CartMutationResponse(BaseModel):
    message: str
    item: CartItemResponse
    totals: CartTotalsResponse


class CartRemovalResponse(BaseModel):
    message: str
    totals: CartTotalsResponse
