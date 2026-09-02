import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import synonym
from sqlalchemy.sql import func

from app.db.database import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    order_id = Column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    amount = Column(
        Numeric(10, 2),
        nullable=False,
    )

    provider = Column(
        String(50),
        nullable=False,
        default="stripe",
    )

    payment_method = synonym("provider")

    status = Column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    transaction_id = Column(
        String(120),
        nullable=True,
        unique=True,
        index=True,
    )

    paid_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    stripe_refund_id = Column(
        String(120),
        nullable=True,
        unique=True,
        index=True,
    )

    refunded_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    timestamp = synonym("created_at")
