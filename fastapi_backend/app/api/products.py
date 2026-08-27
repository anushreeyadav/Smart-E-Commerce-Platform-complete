from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.product import Product
from app.models.user import User, UserRole
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import (
    create_product,
    delete_product,
    get_product_by_id,
    get_products,
    update_product,
)


router = APIRouter(
    tags=["Products"],
)


# ============================================================
# GET ALL PRODUCTS
# PUBLIC
# ============================================================

@router.get(
    "",
    response_model=list[ProductResponse],
    status_code=status.HTTP_200_OK,
)
def list_products(
    category: str | None = Query(default=None),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    popularity: int | None = Query(default=None, ge=0),
    in_stock: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Get all products.

    Public endpoint.
    No authentication required.
    """

    return get_products(
        db,
        category=category,
        min_price=min_price,
        max_price=max_price,
        popularity=popularity,
        in_stock=in_stock,
    )


# ============================================================
# GET PRODUCTS BY CATEGORY
# PUBLIC
# ============================================================

@router.get(
    "/category/{category}",
    response_model=list[ProductResponse],
    status_code=status.HTTP_200_OK,
)
def list_products_by_category(
    category: str,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    popularity: int | None = Query(default=None, ge=0),
    in_stock: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return get_products(
        db,
        category=category,
        min_price=min_price,
        max_price=max_price,
        popularity=popularity,
        in_stock=in_stock,
    )


# ============================================================
# GET SINGLE PRODUCT
# PUBLIC
# ============================================================

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
):
    """
    Get a single product by ID.

    Public endpoint.
    """

    product = get_product_by_id(db, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product


# ============================================================
# CREATE PRODUCT
# ADMIN ONLY
# ============================================================

@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
):
    """
    Create a new product.

    Admin only.
    """

    return create_product(
        db,
        product_data,
    )


# ============================================================
# UPDATE PRODUCT
# ADMIN / STAFF
# ============================================================

@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def update_existing_product(
    product_id: str,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.STAFF,
        )
    ),
):
    """
    Update an existing product.

    Admin and Staff can update products.
    """

    product = get_product_by_id(
        db,
        product_id,
        include_inactive=True,
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return update_product(
        db,
        product,
        product_data,
    )


# ============================================================
# DELETE PRODUCT
# ADMIN ONLY
# ============================================================

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_existing_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
):
    """
    Delete a product.

    Admin only.
    """

    product = get_product_by_id(
        db,
        product_id,
        include_inactive=True,
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    delete_product(
        db,
        product,
    )

    return None
