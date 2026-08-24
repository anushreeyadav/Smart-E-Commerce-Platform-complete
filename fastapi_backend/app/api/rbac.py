from fastapi import APIRouter, Depends

from app.core.dependencies import (
    get_current_user,
    require_roles,
)
from app.models.user import User, UserRole


router = APIRouter(
    prefix="/rbac",
    tags=["Role-Based Access Control"],
)


@router.get("/authenticated")
def authenticated_endpoint(
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Any authenticated user can access this endpoint.
    """

    return {
        "message": "You are authenticated",
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role.value,
    }


@router.get("/admin")
def admin_endpoint(
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
):
    """
    Admin-only endpoint.
    """

    return {
        "message": "Welcome Admin",
        "email": current_user.email,
        "role": current_user.role.value,
    }


@router.get("/staff")
def staff_endpoint(
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.STAFF,
        )
    ),
):
    """
    Admin and Staff can access this endpoint.
    """

    return {
        "message": "Welcome Admin/Staff",
        "email": current_user.email,
        "role": current_user.role.value,
    }


@router.get("/customer")
def customer_endpoint(
    current_user: User = Depends(
        require_roles(UserRole.CUSTOMER)
    ),
):
    """
    Customer-only endpoint.
    """

    return {
        "message": "Welcome Customer",
        "email": current_user.email,
        "role": current_user.role.value,
    }