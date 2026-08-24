from __future__ import annotations

import os
from functools import lru_cache

from fastapi import HTTPException, status


@lru_cache(maxsize=1)
def get_stripe_client():
    try:
        import stripe
    except ImportError as exc:  # pragma: no cover - import guard
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe SDK is not installed",
        ) from exc

    secret_key = os.getenv("STRIPE_SECRET_KEY")

    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured",
        )

    stripe.api_key = secret_key
    return stripe


def get_frontend_url(default: str = "http://localhost:3000") -> str:
    return os.getenv("FRONTEND_URL", default).rstrip("/")

