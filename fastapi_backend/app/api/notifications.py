import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.notification import (
    MarkNotificationsReadRequest,
    MarkNotificationsReadResponse,
    NotificationListResponse,
)
from app.services.notification_service import (
    list_notifications_for_user,
    mark_notifications_as_read,
)


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=NotificationListResponse,
)
def get_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    read: bool | None = Query(
        default=None,
        description="Filter by read status: true, false, or omit for all.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = list_notifications_for_user(
        db,
        current_user.id,
        read_status=read,
        page=page,
        page_size=page_size,
    )

    return NotificationListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=max(1, math.ceil(total / page_size)) if total else 0,
    )


@router.post(
    "/read",
    response_model=MarkNotificationsReadResponse,
)
def mark_notifications_read(
    request: MarkNotificationsReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated_count = mark_notifications_as_read(
        db,
        user_id=current_user.id,
        notification_ids=request.notification_ids,
        mark_all=request.mark_all,
    )

    return {
        "message": "Notifications marked as read.",
        "updated_count": updated_count,
    }
