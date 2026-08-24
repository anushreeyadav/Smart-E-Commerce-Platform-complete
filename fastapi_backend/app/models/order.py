import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func

from app.db.database import Base
from app.models.payment import PaymentStatus


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        Enum(OrderStatus),
        nullable=False,
        default=OrderStatus.PENDING,
    )

    payment_status = Column(
        String(20),
        nullable=False,
        default=PaymentStatus.PENDING.value,
    )

    total_amount = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
    )

    payment_method = Column(
        String(50),
        nullable=False,
        default="stripe",
    )

    currency = Column(
        String(3),
        nullable=False,
        default="usd",
    )

    stripe_checkout_session_id = Column(
        String(120),
        nullable=True,
        unique=True,
        index=True,
    )

    stripe_payment_intent_id = Column(
        String(120),
        nullable=True,
        unique=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    order_id = Column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id = Column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    quantity = Column(
        Integer,
        nullable=False,
    )

    unit_price = Column(
        Numeric(10, 2),
        nullable=False,
    )
