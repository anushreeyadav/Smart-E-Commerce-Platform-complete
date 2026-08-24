from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cart import Cart
from app.models.product import Product
from app.models.user import User, UserRole
from app.schemas.cart import (
    CartAddRequest,
    CartItemResponse,
    CartMutationResponse,
    CartRemovalResponse,
    CartResponse,
    CartTotalsResponse,
    CartUpdateRequest,
)


MONEY_QUANTIZER = Decimal("0.01")


def _money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)


def _require_customer(user: User) -> None:
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can use the cart",
        )


def _get_product_or_404(db: Session, product_id: str) -> Product:
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product


def _get_cart_item(
    db: Session,
    *,
    user_id: str,
    product_id: str,
) -> Cart | None:
    return (
        db.query(Cart)
        .filter(
            Cart.user_id == user_id,
            Cart.product_id == product_id,
        )
        .first()
    )


def _build_item_response(cart_item: Cart, product: Product) -> CartItemResponse:
    unit_price = _money(product.price)
    item_total = _money(unit_price * cart_item.quantity)

    return CartItemResponse(
        id=cart_item.id,
        user_id=cart_item.user_id,
        product_id=cart_item.product_id,
        quantity=cart_item.quantity,
        unit_price=unit_price,
        item_total=item_total,
        product=product,
    )


def _build_totals(
    items: list[CartItemResponse],
    *,
    tax_rate: Decimal = Decimal("0.00"),
) -> CartTotalsResponse:
    cart_total = _money(
        sum((item.item_total for item in items), Decimal("0.00"))
    )
    normalized_tax_rate = Decimal(str(tax_rate)).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )
    tax = _money(cart_total * normalized_tax_rate)
    grand_total = _money(cart_total + tax)

    return CartTotalsResponse(
        cart_total=cart_total,
        tax_rate=normalized_tax_rate,
        tax=tax,
        grand_total=grand_total,
        total_items=sum(item.quantity for item in items),
    )


def add_item_to_cart(
    db: Session,
    user: User,
    request: CartAddRequest,
) -> CartMutationResponse:
    _require_customer(user)

    if request.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than 0",
        )

    product = _get_product_or_404(db, request.product_id)

    if product.stock <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is out of stock",
        )

    existing_item = _get_cart_item(
        db,
        user_id=user.id,
        product_id=request.product_id,
    )

    new_quantity = request.quantity
    if existing_item:
        new_quantity += existing_item.quantity

    if new_quantity > product.stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested quantity exceeds available stock",
        )

    if existing_item:
        existing_item.quantity = new_quantity
        cart_item = existing_item
    else:
        cart_item = Cart(
            user_id=user.id,
            product_id=request.product_id,
            quantity=request.quantity,
        )
        db.add(cart_item)

    db.commit()
    db.refresh(cart_item)

    return CartMutationResponse(
        message="Product added to cart",
        item=_build_item_response(cart_item, product),
        totals=_build_totals(get_cart_items(db, user)),
    )


def update_cart_item(
    db: Session,
    user: User,
    request: CartUpdateRequest,
) -> CartMutationResponse:
    _require_customer(user)

    if request.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than 0",
        )

    cart_item = _get_cart_item(
        db,
        user_id=user.id,
        product_id=request.product_id,
    )

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )

    product = _get_product_or_404(db, request.product_id)

    if request.quantity > product.stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested quantity exceeds available stock",
        )

    cart_item.quantity = request.quantity
    db.commit()
    db.refresh(cart_item)

    return CartMutationResponse(
        message="Cart item updated successfully",
        item=_build_item_response(cart_item, product),
        totals=_build_totals(get_cart_items(db, user)),
    )


def remove_cart_item(
    db: Session,
    user: User,
    product_id: str,
) -> CartRemovalResponse:
    _require_customer(user)

    cart_item = _get_cart_item(
        db,
        user_id=user.id,
        product_id=product_id,
    )

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )

    db.delete(cart_item)
    db.commit()

    return CartRemovalResponse(
        message="Product removed from cart successfully",
        totals=_build_totals(get_cart_items(db, user)),
    )


def get_cart_items(
    db: Session,
    user: User,
) -> list[CartItemResponse]:
    _require_customer(user)

    rows = (
        db.query(Cart, Product)
        .join(Product, Product.id == Cart.product_id)
        .filter(Cart.user_id == user.id)
        .order_by(Cart.id.asc())
        .all()
    )

    return [
        _build_item_response(cart_item, product)
        for cart_item, product in rows
    ]


def get_cart(
    db: Session,
    user: User,
    *,
    tax_rate: Decimal = Decimal("0.00"),
) -> CartResponse:
    items = get_cart_items(db, user)
    return CartResponse(
        items=items,
        totals=_build_totals(items, tax_rate=tax_rate),
    )
