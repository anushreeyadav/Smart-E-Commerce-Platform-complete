from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: NotificationType
    message: str
    read_status: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class MarkNotificationsReadRequest(BaseModel):
    notification_ids: list[str] = Field(default_factory=list)
    mark_all: bool = False

    @model_validator(mode="after")
    def require_notification_ids_or_mark_all(self):
        if not self.notification_ids and not self.mark_all:
            raise ValueError(
                "Provide notification_ids or set mark_all to true."
            )
        return self


class MarkNotificationsReadResponse(BaseModel):
    message: str
    updated_count: int


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    page: int
    page_size: int
    total: int
    total_pages: int