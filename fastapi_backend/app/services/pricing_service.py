from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status

from app.core.config import BASE_CURRENCY, CURRENCY_RATES

_QUANTIZER = Decimal("0.01")


def normalize_currency(currency: str | None) -> str:
    normalized = (currency or "").strip().lower()
    if not normalized:
        normalized = BASE_CURRENCY
    if normalized not in CURRENCY_RATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported currency '{currency}'. "
                f"Supported currencies: {', '.join(sorted(CURRENCY_RATES))}."
            ),
        )
    return normalized


def convert_from_base(amount: Decimal, currency: str) -> Decimal:
    rate = Decimal(str(CURRENCY_RATES[currency]))
    return (amount * rate).quantize(_QUANTIZER, rounding=ROUND_HALF_UP)
