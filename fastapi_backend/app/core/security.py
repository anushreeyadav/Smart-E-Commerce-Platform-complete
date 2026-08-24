import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext


load_dotenv()


# ============================================================
# JWT CONFIGURATION
# ============================================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "development-secret-key-change-this",
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "30",
    )
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv(
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "7",
    )
)


# ============================================================
# PASSWORD HASHING
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    """
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plain-text password against
    its bcrypt hash.
    """
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# ============================================================
# ACCESS TOKEN
# ============================================================

def create_access_token(
    data: Dict[str, Any],
) -> str:
    """
    Create a JWT access token.
    """

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    to_encode.update(
        {
            "exp": expire,
            "type": "access",
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return encoded_jwt


# ============================================================
# REFRESH TOKEN
# ============================================================

def create_refresh_token(
    data: Dict[str, Any],
) -> str:
    """
    Create a JWT refresh token.
    """

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
    )

    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return encoded_jwt


# ============================================================
# DECODE TOKEN
# ============================================================

def decode_token(
    token: str,
) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Returns:
        Dictionary containing token payload
        if valid.

        None if token is invalid or expired.
    """

    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        return payload

    except JWTError:

        return None