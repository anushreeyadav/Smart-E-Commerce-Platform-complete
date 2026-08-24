from tests.conftest import add_to_cart


def _checkout(client, headers):
    return client.post(
        "/checkout",
        json={"payment_method": "stripe", "currency": "usd"},
        headers=headers,
    )


def test_checkout_confirms_order_and_notifies(client, customer, customer_headers, product, _no_real_email):
    add_to_cart(client, customer_headers, product.id, 2)

    response = _checkout(client, customer_headers)
    assert response.status_code == 201

    body = response.json()
    assert body["order"]["status"] == "confirmed"

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert notifications["total"] == 1
    assert notifications["items"][0]["type"] == "order_confirmed"
    assert notifications["items"][0]["read_status"] is False

    assert len(_no_real_email) == 1
    assert "Order confirmed" in _no_real_email[0]["subject"]
    assert _no_real_email[0]["recipient"] == customer.email


def test_order_status_valid_transition_shipped_then_delivered(
    client, customer, customer_headers, staff_headers, product, _no_real_email
):
    add_to_cart(client, customer_headers, product.id, 1)
    order_id = _checkout(client, customer_headers).json()["order"]["id"]

    pay_response = client.post(
        f"/payments/{order_id}/confirm",
        json={"provider": "stripe"},
        headers=customer_headers,
    )
    assert pay_response.status_code == 200

    shipped = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "shipped"},
        headers=staff_headers,
    )
    assert shipped.status_code == 200
    assert shipped.json()["status"] == "shipped"

    delivered = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "delivered"},
        headers=staff_headers,
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"

    notifications = client.get("/notifications", headers=customer_headers).json()
    types = {item["type"] for item in notifications["items"]}
    assert {"order_confirmed", "payment_success", "order_shipped", "order_delivered"} <= types


def test_order_status_rejects_invalid_transition(
    client, customer, customer_headers, staff_headers, product
):
    add_to_cart(client, customer_headers, product.id, 1)
    order_id = _checkout(client, customer_headers).json()["order"]["id"]

    response = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "shipped"},
        headers=staff_headers,
    )
    assert response.status_code == 400


def test_order_status_noop_does_not_duplicate_notification(
    client, customer, customer_headers, staff_headers, product
):
    add_to_cart(client, customer_headers, product.id, 1)
    order_id = _checkout(client, customer_headers).json()["order"]["id"]

    client.post(
        f"/payments/{order_id}/confirm",
        json={"provider": "stripe"},
        headers=customer_headers,
    )

    first = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "shipped"},
        headers=staff_headers,
    )
    assert first.status_code == 200

    second = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "shipped"},
        headers=staff_headers,
    )
    assert second.status_code == 200

    notifications = client.get(
        "/notifications?read=false", headers=customer_headers
    ).json()
    shipped_count = sum(
        1 for item in notifications["items"] if item["type"] == "order_shipped"
    )
    assert shipped_count == 1


def test_customer_cannot_change_order_status(client, customer, customer_headers, product):
    add_to_cart(client, customer_headers, product.id, 1)
    order_id = _checkout(client, customer_headers).json()["order"]["id"]

    response = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "shipped"},
        headers=customer_headers,
    )
    assert response.status_code == 403


def test_customer_cannot_view_another_customers_order(
    client, customer, customer_headers, other_customer_headers, product
):
    add_to_cart(client, customer_headers, product.id, 1)
    order_id = _checkout(client, customer_headers).json()["order"]["id"]

    response = client.get(f"/orders/{order_id}", headers=other_customer_headers)
    assert response.status_code == 403
