import os


# Customer returns must be requested within this many days of delivery.
RETURN_WINDOW_DAYS = int(os.getenv("RETURN_WINDOW_DAYS", "7"))

# Product prices and Payment/Order amounts are stored in this currency.
BASE_CURRENCY = "inr"

# Currencies customers may check out in, and their rate from BASE_CURRENCY.
# Single-currency store: only INR is supported.
CURRENCY_RATES: dict[str, float] = {
    "inr": 1.0,
}
