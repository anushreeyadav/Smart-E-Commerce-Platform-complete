from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
)


def create_product(
    db: Session,
    product_data: ProductCreate,
) -> Product:

    product = Product(
        name=product_data.name,
        description=product_data.description,
        category=product_data.category,
        price=product_data.price,
        stock=product_data.stock,
        images=product_data.images,
        popularity=product_data.popularity,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def get_products(
    db: Session,
    *,
    category: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    popularity: int | None = None,
    in_stock: bool | None = None,
) -> list[Product]:

    query = db.query(Product)

    if category:
        query = query.filter(Product.category.ilike(category))

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if popularity is not None:
        query = query.filter(Product.popularity >= popularity)

    if in_stock is True:
        query = query.filter(Product.stock > 0)
    elif in_stock is False:
        query = query.filter(Product.stock <= 0)

    return (
        query
        .order_by(Product.popularity.desc(), Product.created_at.desc())
        .all()
    )


def get_product_by_id(
    db: Session,
    product_id: str,
) -> Optional[Product]:

    return (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )


def update_product(
    db: Session,
    product: Product,
    product_data: ProductUpdate,
) -> Product:

    update_data = product_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


def delete_product(
    db: Session,
    product: Product,
) -> None:

    db.delete(product)
    db.commit()
