import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ReturnRequestStatus(str, enum.Enum):
    PENDING = "pending"  # customer-facing label: "Requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    REFUNDED = "refunded"


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason = Column(String(500), nullable=False)
    comments = Column(Text, nullable=True)
    status = Column(
        Enum(
            ReturnRequestStatus,
            native_enum=False,
            create_constraint=True,
            name="return_request_status",
        ),
        nullable=False,
        default=ReturnRequestStatus.PENDING,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    reviewed_by = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comment = Column(Text, nullable=True)

    order = relationship("Order", back_populates="return_request")
    user = relationship("User", back_populates="return_requests", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    history = relationship(
        "ReturnRequestHistory",
        back_populates="return_request",
        cascade="all, delete-orphan",
        order_by="ReturnRequestHistory.created_at",
    )

    @property
    def reviewed_by_name(self) -> str | None:
        return self.reviewer.name if self.reviewer else None
