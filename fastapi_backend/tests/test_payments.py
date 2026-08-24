import json

from tests.conftest import add_to_cart


def _checkout(client, headers):
    return client.post(
        "/checkout",
        json={"payment_method": "stripe", "currency": "usd"},
        headers=headers,
    )


def _stripe_event(event_type: str, order_id: str, payment_intent_id: str) -> bytes:
    return json.dumps(
        {
            "type": event_type,
            "data": {
                "object": {
                    "id": payment_intent_id,
                    "payment_intent": payment_intent_id,
                    "metadata": {"order_id": order_id},
                }
            },
        }
    ).encode()


def test_webhook_payment_succeeded_notifies_and_emails(
    client, customer, customer_headers, product, _no_real_email
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]
    payment_intent_id = order["stripe_payment_intent_id"]

    response = client.post(
        "/webhooks/stripe",
        content=_stripe_event("payment_intent.succeeded", order["id"], payment_intent_id),
        headers={"Stripe-Signature": "test-signature"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "paid"

    order_after = client.get(f"/orders/{order['id']}", headers=customer_headers).json()
    assert order_after["status"] == "paid"
    assert order_after["payment_status"] == "paid"

    notifications = client.get("/notifications", headers=customer_headers).json()
    payment_success = [
        item for item in notifications["items"] if item["type"] == "payment_success"
    ]
    assert len(payment_success) == 1

    payment_emails = [e for e in _no_real_email if "Payment successful" in e["subject"]]
    assert len(payment_emails) == 1


def test_webhook_retry_does_not_duplicate_notification(
    client, customer, customer_headers, product, _no_real_email
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]
    payment_intent_id = order["stripe_payment_intent_id"]

    payload = _stripe_event("payment_intent.succeeded", order["id"], payment_intent_id)

    first = client.post(
        "/webhooks/stripe", content=payload, headers={"Stripe-Signature": "sig"}
    )
    second = client.post(
        "/webhooks/stripe", content=payload, headers={"Stripe-Signature": "sig"}
    )

    assert first.status_code == 200
    assert second.status_code == 200

    notifications = client.get("/notifications", headers=customer_headers).json()
    payment_success = [
        item for item in notifications["items"] if item["type"] == "payment_success"
    ]
    assert len(payment_success) == 1

    payment_emails = [e for e in _no_real_email if "Payment successful" in e["subject"]]
    assert len(payment_emails) == 1


def test_webhook_payment_failed_notifies(
    client, customer, customer_headers, product, _no_real_email
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]
    payment_intent_id = order["stripe_payment_intent_id"]

    response = client.post(
        "/webhooks/stripe",
        content=_stripe_event(
            "payment_intent.payment_failed", order["id"], payment_intent_id
        ),
        headers={"Stripe-Signature": "sig"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"

    notifications = client.get("/notifications", headers=customer_headers).json()
    failed = [item for item in notifications["items"] if item["type"] == "payment_failed"]
    assert len(failed) == 1

    failure_emails = [e for e in _no_real_email if "Payment failed" in e["subject"]]
    assert len(failure_emails) == 1


def test_manual_confirm_uses_same_notification_flow_as_webhook(
    client, customer, customer_headers, product, _no_real_email
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]

    response = client.post(
        f"/payments/{order['id']}/confirm",
        json={"provider": "stripe"},
        headers=customer_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "paid"

    notifications = client.get("/notifications", headers=customer_headers).json()
    payment_success = [
        item for item in notifications["items"] if item["type"] == "payment_success"
    ]
    assert len(payment_success) == 1

    payment_emails = [e for e in _no_real_email if "Payment successful" in e["subject"]]
    assert len(payment_emails) == 1


def test_manual_confirm_twice_does_not_duplicate(
    client, customer, customer_headers, product, _no_real_email
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]

    client.post(
        f"/payments/{order['id']}/confirm",
        json={"provider": "stripe"},
        headers=customer_headers,
    )
    client.post(
        f"/payments/{order['id']}/confirm",
        json={"provider": "stripe"},
        headers=customer_headers,
    )

    notifications = client.get("/notifications", headers=customer_headers).json()
    payment_success = [
        item for item in notifications["items"] if item["type"] == "payment_success"
    ]
    assert len(payment_success) == 1
