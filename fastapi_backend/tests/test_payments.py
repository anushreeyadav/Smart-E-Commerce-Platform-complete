import json

from tests.conftest import FakeCheckoutSessionApi, add_to_cart


def _checkout(client, headers):
    return client.post(
        "/checkout",
        json={"payment_method": "stripe", "currency": "inr"},
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


# ---------------------------------------------------------------------------
# Stripe-verified sync fallback: what actually runs when the customer returns
# from Stripe Checkout, so payment status doesn't get stuck at "pending" in
# environments/timing where the async webhook hasn't landed yet.
# ---------------------------------------------------------------------------


def test_sync_marks_order_paid_when_stripe_confirms_payment(
    client, customer, customer_headers, product, _no_real_email
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]
    session_id = order["stripe_checkout_session_id"]

    # Simulate the customer having actually paid on Stripe's hosted page -
    # this is what stripe.checkout.Session.retrieve would report back.
    FakeCheckoutSessionApi.sessions[session_id] = {
        "id": session_id,
        "status": "complete",
        "payment_status": "paid",
        "payment_intent": "pi_real_completed",
    }

    response = client.post(f"/payments/{order['id']}/sync", headers=customer_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["verified_state"] == "paid"
    assert body["payment"]["status"] == "paid"

    order_after = client.get(f"/orders/{order['id']}", headers=customer_headers).json()
    assert order_after["status"] == "paid"
    assert order_after["payment_status"] == "paid"
    assert order_after["stripe_payment_intent_id"] == "pi_real_completed"

    notifications = client.get("/notifications", headers=customer_headers).json()
    payment_success = [
        item for item in notifications["items"] if item["type"] == "payment_success"
    ]
    assert len(payment_success) == 1

    payment_emails = [e for e in _no_real_email if "Payment successful" in e["subject"]]
    assert len(payment_emails) == 1


def test_sync_is_idempotent_and_does_not_duplicate_notifications(
    client, customer, customer_headers, product
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]
    session_id = order["stripe_checkout_session_id"]

    FakeCheckoutSessionApi.sessions[session_id] = {
        "id": session_id,
        "status": "complete",
        "payment_status": "paid",
        "payment_intent": "pi_real_completed",
    }

    first = client.post(f"/payments/{order['id']}/sync", headers=customer_headers)
    second = client.post(f"/payments/{order['id']}/sync", headers=customer_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["verified_state"] == "already_settled"

    notifications = client.get("/notifications", headers=customer_headers).json()
    payment_success = [
        item for item in notifications["items"] if item["type"] == "payment_success"
    ]
    assert len(payment_success) == 1


def test_sync_leaves_status_pending_while_stripe_session_still_open(
    client, customer, customer_headers, product
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]
    # No entry seeded for this session id -> FakeCheckoutSessionApi.retrieve
    # falls back to its default "open"/"unpaid" response, matching a
    # customer who hasn't finished paying yet.

    response = client.post(f"/payments/{order['id']}/sync", headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["verified_state"] == "pending"

    order_after = client.get(f"/orders/{order['id']}", headers=customer_headers).json()
    assert order_after["status"] == "confirmed"
    assert order_after["payment_status"] == "pending"


def test_sync_marks_order_failed_when_checkout_session_expired(
    client, customer, customer_headers, product, _no_real_email
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]
    session_id = order["stripe_checkout_session_id"]

    FakeCheckoutSessionApi.sessions[session_id] = {
        "id": session_id,
        "status": "expired",
        "payment_status": "unpaid",
        "payment_intent": None,
    }

    response = client.post(f"/payments/{order['id']}/sync", headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["verified_state"] == "failed"

    order_after = client.get(f"/orders/{order['id']}", headers=customer_headers).json()
    assert order_after["payment_status"] == "failed"

    notifications = client.get("/notifications", headers=customer_headers).json()
    failed = [item for item in notifications["items"] if item["type"] == "payment_failed"]
    assert len(failed) == 1


def test_sync_rejects_syncing_someone_elses_order(
    client, customer, customer_headers, other_customer_headers, product
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]

    response = client.post(f"/payments/{order['id']}/sync", headers=other_customer_headers)
    assert response.status_code == 403


def test_sync_returns_404_for_missing_order(client, customer_headers):
    response = client.post("/payments/does-not-exist/sync", headers=customer_headers)
    assert response.status_code == 404


def test_admin_can_use_sync_as_the_confirm_payment_action(
    client, customer, customer_headers, admin_headers, product
):
    """This is the backend for the admin "Confirm Payment" button (which
    replaced the old manual "Mark as Paid" status click): staff/admin verify
    a specific order's payment with Stripe directly, the same way the
    customer-facing post-checkout sync does."""

    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]
    session_id = order["stripe_checkout_session_id"]

    FakeCheckoutSessionApi.sessions[session_id] = {
        "id": session_id,
        "status": "complete",
        "payment_status": "paid",
        "payment_intent": "pi_admin_confirmed",
    }

    response = client.post(f"/payments/{order['id']}/sync", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["verified_state"] == "paid"

    admin_orders = client.get("/orders", headers=admin_headers).json()
    listed = next(item for item in admin_orders["items"] if item["id"] == order["id"])
    assert listed["payment_status"] == "paid"
    assert listed["status"] == "paid"


def test_webhook_checkout_session_expired_marks_payment_failed(
    client, customer, customer_headers, product, _no_real_email
):
    add_to_cart(client, customer_headers, product.id, 1)
    order = _checkout(client, customer_headers).json()["order"]

    payload = json.dumps(
        {
            "type": "checkout.session.expired",
            "data": {
                "object": {
                    "id": order["stripe_checkout_session_id"],
                    "payment_intent": None,
                    "metadata": {"order_id": order["id"]},
                }
            },
        }
    ).encode()

    response = client.post(
        "/webhooks/stripe", content=payload, headers={"Stripe-Signature": "sig"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"

    order_after = client.get(f"/orders/{order['id']}", headers=customer_headers).json()
    assert order_after["payment_status"] == "failed"
