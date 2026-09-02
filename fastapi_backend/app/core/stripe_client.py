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


def stripe_field(obj, key: str, default=None):
    """Safely read a field from a Stripe API response object (or a plain
    dict standing in for one, e.g. in tests).

    Recent stripe-python versions (this project runs 15.x) no longer make
    StripeObject behave like a dict - calling .get() on one raises
    AttributeError ("'get' is a dict method, but a StripeObject is not a
    dict"). Bracket access (obj[key]), on the other hand, is supported by
    both a real StripeObject and a plain dict, and both raise KeyError for a
    missing key - so that's the one access pattern that's safe everywhere a
    Stripe response (or a test double for one) is read.
    """
    if obj is None:
        return default
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default

