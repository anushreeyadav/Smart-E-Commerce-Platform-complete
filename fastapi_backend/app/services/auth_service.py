from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:

    return (
        db.query(User)
        .filter(User.email == email)
        .first()
    )


def create_user(
    db: Session,
    name: str,
    email: str,
    password: str,
    role: UserRole = UserRole.CUSTOMER,
) -> User:

    user = User(
        name=name,
        email=email,
        password=hash_password(password),
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_or_create_social_user(
    db: Session,
    *,
    email: str,
    name: Optional[str] = None,
) -> User:
    """
    Create a passwordless customer account for a social login user.
    """

    display_name = name or email.split("@", 1)[0]

    user = get_user_by_email(
        db,
        email,
    )

    if user:
        if display_name and user.name != display_name:
            user.name = display_name
            db.commit()
            db.refresh(user)

        return user

    user = User(
        name=display_name,
        email=email,
        password=None,
        role=UserRole.CUSTOMER,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
