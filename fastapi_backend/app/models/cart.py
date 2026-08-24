import uuid

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class Cart(Base):
    __tablename__ = "cart_items"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id = Column(
        String(36),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    product_id = Column(
        String(36),
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    quantity = Column(
        Integer,
        nullable=False,
        default=1,
    )

    user = relationship(
        "User",
        back_populates="cart_items",
    )

    product = relationship(
        "Product",
        back_populates="cart_items",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_cart_user_product",
        ),
    )
