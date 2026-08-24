import os
from typing import Any, Dict

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from dotenv import load_dotenv

load_dotenv()


AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")

if not AUTH0_DOMAIN:
    raise RuntimeError("AUTH0_DOMAIN is not configured")

if not AUTH0_AUDIENCE:
    raise RuntimeError("AUTH0_AUDIENCE is not configured")


AUTH0_ISSUER = f"https://{AUTH0_DOMAIN}/"

ALGORITHMS = ["RS256"]

security = HTTPBearer()


def get_jwks_url() -> str:
    return f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"


async def get_jwks() -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(get_jwks_url())

        response.raise_for_status()

        return response.json()

    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve Auth0 signing keys",
        )


async def get_current_auth0_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:

    token = credentials.credentials

    jwks = await get_jwks()

    try:
        unverified_header = jwt.get_unverified_header(token)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    rsa_key = {}

    for key in jwks.get("keys", []):
        if key.get("kid") == unverified_header.get("kid"):
            rsa_key = {
                "kty": key.get("kty"),
                "kid": key.get("kid"),
                "use": key.get("use"),
                "n": key.get("n"),
                "e": key.get("e"),
            }
            break

    if not rsa_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find appropriate Auth0 signing key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=ALGORITHMS,
            audience=AUTH0_AUDIENCE,
            issuer=AUTH0_ISSUER,
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except jwt.JWTClaimsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload