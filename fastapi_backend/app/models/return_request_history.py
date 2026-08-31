import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ReturnRequestHistory(Base):
    __tablename__ = "return_request_history"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    return_request_id = Column(
        String(36),
        ForeignKey("return_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    previous_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=False)
    comment = Column(Text, nullable=True)

    changed_by = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    return_request = relationship("ReturnRequest", back_populates="history")
    changed_by_user = relationship("User")

    @property
    def changed_by_name(self) -> str | None:
        return self.changed_by_user.name if self.changed_by_user else None
