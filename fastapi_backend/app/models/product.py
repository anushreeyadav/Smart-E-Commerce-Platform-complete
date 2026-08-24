from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    price = Column(
        Numeric(10, 2),
        nullable=False,
    )

    category = Column(
        String(100),
        nullable=False,
        default="general",
        index=True,
    )

    stock = Column(
        Integer,
        nullable=False,
        default=0,
    )

    images = Column(
        JSON,
        nullable=False,
        default=list,
    )

    popularity = Column(
        Integer,
        nullable=False,
        default=0,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    cart_items = relationship(
        "Cart",
        back_populates="product",
        cascade="all, delete-orphan",
    )
