from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )