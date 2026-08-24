from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.cart import (
    CartAddRequest,
    CartMutationResponse,
    CartRemoveRequest,
    CartRemovalResponse,
    CartResponse,
    CartUpdateRequest,
)
from app.services.cart_service import (
    add_item_to_cart,
    get_cart,
    remove_cart_item,
    update_cart_item,
)
from app.services.connection_manager import manager


router = APIRouter(tags=["Cart"])


@router.post(
    "/add",
    response_model=CartMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/",
    response_model=CartMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_cart(
    request: CartAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response = add_item_to_cart(
        db,
        current_user,
        request,
    )

    await manager.send_to_user(
        current_user.id,
        "cart_updated",
        {
            "message": response.message,
            "total_items": response.totals.total_items,
            "cart_total": str(response.totals.cart_total),
        },
    )

    return response


@router.put(
    "/update",
    response_model=CartMutationResponse,
)
@router.put(
    "/",
    response_model=CartMutationResponse,
)
async def update_cart(
    request: CartUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response = update_cart_item(
        db,
        current_user,
        request,
    )

    await manager.send_to_user(
        current_user.id,
        "cart_updated",
        {
            "message": response.message,
            "total_items": response.totals.total_items,
            "cart_total": str(response.totals.cart_total),
        },
    )

    return response


@router.delete(
    "/remove",
    response_model=CartRemovalResponse,
)
@router.delete(
    "/",
    response_model=CartRemovalResponse,
)
async def remove_from_cart(
    request: CartRemoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response = remove_cart_item(
        db,
        current_user,
        request.product_id,
    )

    await manager.send_to_user(
        current_user.id,
        "cart_updated",
        {
            "message": response.message,
            "total_items": response.totals.total_items,
            "cart_total": str(response.totals.cart_total),
        },
    )

    return response


@router.get(
    "",
    response_model=CartResponse,
)
def get_current_cart(
    tax_rate: Decimal = Query(default=Decimal("0.00"), ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_cart(
        db,
        current_user,
        tax_rate=tax_rate,
    )