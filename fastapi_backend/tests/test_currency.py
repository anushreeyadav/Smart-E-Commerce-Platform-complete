from decimal import Decimal

from tests.conftest import add_to_cart


def test_checkout_currencies_endpoint_lists_inr_only(client):
    response = client.get("/checkout/currencies")

    assert response.status_code == 200
    body = response.json()
    assert body["base_currency"] == "inr"
    assert body["currencies"] == [{"code": "inr", "rate_from_base": 1.0}]


def test_checkout_defaults_to_inr_with_no_conversion(
    client, customer_headers, product, _no_real_email
):
    add_to_cart(client, customer_headers, product.id, 2)

    response = client.post(
        "/checkout",
        json={"payment_method": "stripe"},
        headers=customer_headers,
    )

    assert response.status_code == 201
    order = response.json()["order"]
    assert order["currency"] == "inr"

    expected_total = (Decimal(str(product.price)) * 2).quantize(Decimal("0.01"))
    assert Decimal(str(order["total_amount"])) == expected_total
    assert Decimal(str(order["items"][0]["unit_price"])) == Decimal(str(product.price)).quantize(
        Decimal("0.01")
    )


def test_checkout_rejects_usd(client, customer_headers, product, _no_real_email):
    add_to_cart(client, customer_headers, product.id, 1)

    response = client.post(
        "/checkout",
        json={"payment_method": "stripe", "currency": "usd"},
        headers=customer_headers,
    )

    assert response.status_code == 400
    assert "Unsupported currency" in response.json()["detail"]
