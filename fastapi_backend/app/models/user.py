import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    CUSTOMER = "customer"


class User(Base):
    __tablename__ = "users"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name = Column(
        String(100),
        nullable=False,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password = Column(
        String(255),
        nullable=True,
    )

    role = Column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.CUSTOMER,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    cart_items = relationship(
        "Cart",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )