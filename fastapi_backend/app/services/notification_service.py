from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType


def create_notification(
    db: Session,
    *,
    user_id: str,
    notification_type: NotificationType,
    message: str,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        message=message,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


def list_notifications_for_user(
    db: Session,
    user_id: str,
    *,
    read_status: bool | None = None,
    page: int = 1,
    page_size: int | None = None,
) -> tuple[list[Notification], int]:
    query = db.query(Notification).filter(Notification.user_id == user_id)

    if read_status is not None:
        query = query.filter(Notification.read_status == read_status)

    total = query.count()

    query = query.order_by(Notification.timestamp.desc())

    if page_size is not None:
        query = query.offset((max(page, 1) - 1) * page_size).limit(page_size)

    return query.all(), total


def mark_notifications_as_read(
    db: Session,
    *,
    user_id: str,
    notification_ids: list[str],
    mark_all: bool,
) -> int:
    query = db.query(Notification).filter(
        Notification.user_id == user_id
    )

    if not mark_all:
        query = query.filter(
            Notification.id.in_(notification_ids)
        )

    updated_count = query.update(
        {Notification.read_status: True},
        synchronize_session=False,
    )

    db.commit()

    return updated_count
    