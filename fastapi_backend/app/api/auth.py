import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth0 import get_current_auth0_user
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import (
    create_user,
    get_or_create_social_user,
    get_user_by_email,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# AUTH0 CURRENT USER - TEST ENDPOINT
# ============================================================

@router.get("/auth0/me")
async def auth0_me(
    current_user=Depends(get_current_auth0_user),
):
    """
    Return the authenticated Auth0 user.

    This endpoint is used to verify that a valid Auth0
    access token can be validated by FastAPI.
    """

    return {
        "authenticated": True,
        "auth0_user": current_user,
    }


# ============================================================
# REGISTER
# ============================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new customer account.
    """

    existing_user = get_user_by_email(
        db,
        request.email,
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = create_user(
        db=db,
        name=request.name,
        email=request.email,
        password=request.password,
    )

    return user


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Login using email and password.

    Returns:
    - Access token
    - Refresh token
    """

    user = get_user_by_email(
        db,
        request.email,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account does not use password login",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(
        request.password,
        user.password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub": user.id,
            "role": user.role.value,
        }
    )

    refresh_token = create_refresh_token(
        data={
            "sub": user.id,
            "role": user.role.value,
        }
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


# ============================================================
# REFRESH TOKEN
# ============================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a new access token using a refresh token.
    """

    payload = decode_token(
        request.refresh_token
    )

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_access_token = create_access_token(
        data={
            "sub": user.id,
            "role": user.role.value,
        }
    )

    new_refresh_token = create_refresh_token(
        data={
            "sub": user.id,
            "role": user.role.value,
        }
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


# ============================================================
# AUTH0 SOCIAL LOGIN EXCHANGE
# ============================================================

@router.post(
    "/auth0/login",
    response_model=TokenResponse,
)
async def auth0_login(
    auth0_user=Depends(get_current_auth0_user),
    db: Session = Depends(get_db),
):
    """
    Exchange a valid Auth0 access token for local JWT tokens.

    The user is created automatically if they do not already exist.
    """

    email = auth0_user.get("email")
    name = auth0_user.get("name") or auth0_user.get("nickname")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auth0 token does not contain an email address",
        )

    user = get_or_create_social_user(
        db,
        email=email,
        name=name,
    )

    access_token = create_access_token(
        data={
            "sub": user.id,
            "role": user.role.value,
        }
    )

    refresh_token = create_refresh_token(
        data={
            "sub": user.id,
            "role": user.role.value,
        }
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


# ============================================================
# GET CURRENT USER - LOCAL JWT
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Return the currently authenticated local JWT user.
    """

    return current_user


# ============================================================
# BOOTSTRAP ADMIN
# ============================================================

@router.post(
    "/bootstrap-admin",
)
def bootstrap_admin(
    db: Session = Depends(get_db),
):
    """
    Create the permanent development/admin account.

    Development credentials:

    Email:
        admin@example.com

    Password:
        Admin@12345
    """

    if os.getenv("ALLOW_BOOTSTRAP_ADMIN", "false").lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap admin is disabled",
        )

    admin_email = "admin@example.com"
    admin_password = "Admin@12345"

    existing_admin = (
        db.query(User)
        .filter(User.email == admin_email)
        .first()
    )

    # --------------------------------------------------------
    # If admin already exists
    # --------------------------------------------------------

    if existing_admin:

        if existing_admin.role != UserRole.ADMIN:

            existing_admin.role = UserRole.ADMIN

            db.commit()
            db.refresh(existing_admin)

            return {
                "message": "Existing user promoted to admin",
                "email": existing_admin.email,
                "role": existing_admin.role.value,
            }

        return {
            "message": "Admin account already exists",
            "email": existing_admin.email,
            "role": existing_admin.role.value,
        }

    # --------------------------------------------------------
    # Create new admin
    # --------------------------------------------------------

    admin_user = User(
        name="System Administrator",
        email=admin_email,
        password=hash_password(admin_password),
        role=UserRole.ADMIN,
    )

    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    return {
        "message": "Admin account created successfully",
        "email": admin_user.email,
        "role": admin_user.role.value,
    }
