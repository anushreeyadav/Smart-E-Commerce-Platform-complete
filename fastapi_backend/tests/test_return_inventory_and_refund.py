from datetime import datetime, timezone

import pytest

from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.product import Product


def _delivered_order_with_items(
    db_session,
    client,
    customer,
    customer_headers,
    product,
    *,
    quantity=2,
    with_payment=True,
):
    order = Order(
        user_id=customer.id,
        status=OrderStatus.DELIVERED,
        payment_status=PaymentStatus.PAID.value if with_payment else PaymentStatus.PENDING.value,
        total_amount=product.price * quantity,
        delivered_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    db_session.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price,
        )
    )
    # Mirror create_order_from_cart: stock is deducted at purchase time, so
    # approving the return later should give it back.
    product.stock -= quantity
    db_session.commit()
    db_session.refresh(product)

    if with_payment:
        db_session.add(
            Payment(
                order_id=order.id,
                amount=order.total_amount,
                provider="stripe",
                status=PaymentStatus.PAID,
                transaction_id=f"pi_test_{order.id[:8]}",
            )
        )
        db_session.commit()

    response = client.post(
        f"/orders/{order.id}/return",
        json={"reason": "Item arrived damaged", "comment": "Corner is cracked."},
        headers=customer_headers,
    )
    assert response.status_code == 201
    return order, response.json()["id"]


# ---------------------------------------------------------------------------
# 1. Inventory management
# ---------------------------------------------------------------------------


def test_approving_return_restocks_the_product(
    db_session, client, customer, customer_headers, admin_headers, product
):
    original_stock = product.stock
    _order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product, quantity=3
    )

    db_session.refresh(product)
    assert product.stock == original_stock - 3

    response = client.post(
        f"/admin/returns/{return_id}/approve",
        json={"comment": "Approved."},
        headers=admin_headers,
    )
    assert response.status_code == 200

    db_session.refresh(product)
    assert product.stock == original_stock


def test_approving_return_restocks_every_item_on_the_order(
    db_session, client, customer, customer_headers, admin_headers, product
):
    second = Product(
        name="Second Widget",
        description="Another widget.",
        category="general",
        price=50,
        stock=10,
        images=[],
        popularity=1,
    )
    db_session.add(second)
    db_session.commit()
    db_session.refresh(second)

    order = Order(
        user_id=customer.id,
        status=OrderStatus.DELIVERED,
        payment_status=PaymentStatus.PAID.value,
        total_amount=500,
        delivered_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    db_session.add(OrderItem(order_id=order.id, product_id=product.id, quantity=2, unit_price=product.price))
    db_session.add(OrderItem(order_id=order.id, product_id=second.id, quantity=4, unit_price=second.price))
    product.stock -= 2
    second.stock -= 4
    db_session.commit()
    db_session.refresh(product)
    db_session.refresh(second)

    product_stock_before = product.stock
    second_stock_before = second.stock

    create = client.post(
        f"/orders/{order.id}/return",
        json={"reason": "Wrong items shipped"},
        headers=customer_headers,
    )
    assert create.status_code == 201
    return_id = create.json()["id"]

    approve = client.post(f"/admin/returns/{return_id}/approve", json={}, headers=admin_headers)
    assert approve.status_code == 200

    db_session.refresh(product)
    db_session.refresh(second)
    assert product.stock == product_stock_before + 2
    assert second.stock == second_stock_before + 4


def test_duplicate_approve_does_not_double_restock(
    db_session, client, customer, customer_headers, admin_headers, product
):
    original_stock = product.stock
    _order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product, quantity=2
    )

    first = client.post(f"/admin/returns/{return_id}/approve", json={}, headers=admin_headers)
    assert first.status_code == 200

    db_session.refresh(product)
    assert product.stock == original_stock

    second = client.post(
        f"/admin/returns/{return_id}/approve", json={"comment": "again"}, headers=admin_headers
    )
    assert second.status_code == 400

    db_session.refresh(product)
    assert product.stock == original_stock


def test_rejecting_return_does_not_restock(
    db_session, client, customer, customer_headers, admin_headers, product
):
    _order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product, quantity=2
    )
    db_session.refresh(product)
    stock_after_purchase = product.stock

    response = client.post(
        f"/admin/returns/{return_id}/reject",
        json={"comment": "Not eligible."},
        headers=admin_headers,
    )
    assert response.status_code == 200

    db_session.refresh(product)
    assert product.stock == stock_after_purchase


def test_restock_failure_rolls_back_the_whole_approval(
    db_session, client, customer, customer_headers, admin_headers, product, monkeypatch
):
    original_stock = product.stock
    _order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product, quantity=2
    )

    def _boom(db, *, order_id):
        raise RuntimeError("inventory service unavailable")

    monkeypatch.setattr("app.services.return_service.restock_return_items", _boom)

    with pytest.raises(RuntimeError):
        client.post(f"/admin/returns/{return_id}/approve", json={}, headers=admin_headers)

    # Nothing committed: return request is still pending, stock untouched.
    listing = client.get("/admin/returns", params={"status": "pending"}, headers=admin_headers)
    ids = [item["id"] for item in listing.json()["items"]]
    assert ids == [return_id]

    db_session.refresh(product)
    assert product.stock == original_stock - 2


# ---------------------------------------------------------------------------
# 2. Payment refund
# ---------------------------------------------------------------------------


def test_refund_requires_a_paid_payment_not_just_any_payment_record(
    db_session, client, customer, customer_headers, admin_headers, product
):
    order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product, with_payment=False
    )
    db_session.add(
        Payment(
            order_id=order.id,
            amount=order.total_amount,
            provider="stripe",
            status=PaymentStatus.FAILED,
            transaction_id="pi_failed",
        )
    )
    db_session.commit()

    approve = client.post(f"/admin/returns/{return_id}/approve", json={}, headers=admin_headers)
    assert approve.status_code == 200

    response = client.post(f"/admin/returns/{return_id}/refund", json={}, headers=admin_headers)
    assert response.status_code == 400


def test_refund_stripe_failure_does_not_corrupt_payment_or_order(
    db_session, client, customer, customer_headers, admin_headers, product, _fake_stripe, monkeypatch
):
    order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product
    )
    approve = client.post(f"/admin/returns/{return_id}/approve", json={}, headers=admin_headers)
    assert approve.status_code == 200

    def _boom(**_kwargs):
        raise RuntimeError("stripe outage")

    monkeypatch.setattr(_fake_stripe.Refund, "create", _boom)

    response = client.post(f"/admin/returns/{return_id}/refund", json={}, headers=admin_headers)
    assert response.status_code == 502

    order_detail = client.get(f"/orders/{order.id}", headers=admin_headers).json()
    assert order_detail["payment_status"] == "paid"

    payment = client.get(f"/payments/{order.id}", headers=admin_headers).json()
    assert payment["status"] == "paid"


def test_successful_refund_updates_payment_status_to_refunded(
    db_session, client, customer, customer_headers, admin_headers, product, _fake_stripe
):
    order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product
    )
    approve = client.post(f"/admin/returns/{return_id}/approve", json={}, headers=admin_headers)
    assert approve.status_code == 200

    response = client.post(
        f"/admin/returns/{return_id}/refund", json={"comment": "Refund issued."}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "refunded"

    payment = client.get(f"/payments/{order.id}", headers=admin_headers).json()
    assert payment["status"] == "refunded"
    assert payment["stripe_refund_id"] is not None
    assert payment["stripe_refund_id"] == _fake_stripe.Refund.created[0].id
    assert payment["refunded_at"] is not None

    order_detail = client.get(f"/orders/{order.id}", headers=admin_headers).json()
    assert order_detail["payment_status"] == "refunded"

    assert len(_fake_stripe.Refund.calls) == 1
    assert _fake_stripe.Refund.calls[0]["payment_intent"] == f"pi_test_{order.id[:8]}"


def test_duplicate_refund_request_does_not_call_stripe_again(
    db_session, client, customer, customer_headers, admin_headers, product, _fake_stripe
):
    order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product
    )
    approve = client.post(f"/admin/returns/{return_id}/approve", json={}, headers=admin_headers)
    assert approve.status_code == 200

    first = client.post(f"/admin/returns/{return_id}/refund", json={}, headers=admin_headers)
    assert first.status_code == 200

    payment_after_first = client.get(f"/payments/{order.id}", headers=admin_headers).json()
    stored_refund_id = payment_after_first["stripe_refund_id"]
    assert stored_refund_id is not None

    second = client.post(f"/admin/returns/{return_id}/refund", json={}, headers=admin_headers)
    assert second.status_code == 400

    # No second Stripe call was made, and the stored refund stays the one
    # from the first, successful attempt.
    assert len(_fake_stripe.Refund.calls) == 1
    payment_after_second = client.get(f"/payments/{order.id}", headers=admin_headers).json()
    assert payment_after_second["stripe_refund_id"] == stored_refund_id


# ---------------------------------------------------------------------------
# 3. Notifications (email + in-app), only after the operation succeeds
# ---------------------------------------------------------------------------


def test_approve_sends_email_and_in_app_notification(
    db_session, client, customer, customer_headers, admin_headers, product, _no_real_email
):
    _order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product
    )

    response = client.post(
        f"/admin/returns/{return_id}/approve", json={"comment": "Approved."}, headers=admin_headers
    )
    assert response.status_code == 200

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert any(n["type"] == "return_approved" for n in notifications["items"])

    approved_emails = [e for e in _no_real_email if "Return request approved" in e["subject"]]
    assert len(approved_emails) == 1
    assert approved_emails[0]["recipient"] == customer.email


def test_reject_sends_email_and_in_app_notification(
    db_session, client, customer, customer_headers, admin_headers, product, _no_real_email
):
    _order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product
    )

    response = client.post(
        f"/admin/returns/{return_id}/reject",
        json={"comment": "Not eligible for return."},
        headers=admin_headers,
    )
    assert response.status_code == 200

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert any(n["type"] == "return_rejected" for n in notifications["items"])

    rejected_emails = [e for e in _no_real_email if "Return request rejected" in e["subject"]]
    assert len(rejected_emails) == 1
    assert rejected_emails[0]["recipient"] == customer.email


def test_refund_sends_email_and_in_app_notification(
    db_session, client, customer, customer_headers, admin_headers, product, _no_real_email, _fake_stripe
):
    _order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product
    )
    approve = client.post(f"/admin/returns/{return_id}/approve", json={}, headers=admin_headers)
    assert approve.status_code == 200

    response = client.post(
        f"/admin/returns/{return_id}/refund", json={"comment": "Refund issued."}, headers=admin_headers
    )
    assert response.status_code == 200

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert any(n["type"] == "refund_processed" for n in notifications["items"])

    refund_emails = [e for e in _no_real_email if "Refund processed" in e["subject"]]
    assert len(refund_emails) == 1
    assert refund_emails[0]["recipient"] == customer.email


def test_failed_refund_sends_no_refund_notification_or_email(
    db_session, client, customer, customer_headers, admin_headers, product, _no_real_email, _fake_stripe, monkeypatch
):
    _order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product
    )
    approve = client.post(f"/admin/returns/{return_id}/approve", json={}, headers=admin_headers)
    assert approve.status_code == 200

    def _boom(**_kwargs):
        raise RuntimeError("stripe outage")

    monkeypatch.setattr(_fake_stripe.Refund, "create", _boom)

    response = client.post(f"/admin/returns/{return_id}/refund", json={}, headers=admin_headers)
    assert response.status_code == 502

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert not any(n["type"] == "refund_processed" for n in notifications["items"])

    refund_emails = [e for e in _no_real_email if "Refund processed" in e["subject"]]
    assert len(refund_emails) == 0


def test_rejected_return_sends_no_approval_artifacts(
    db_session, client, customer, customer_headers, admin_headers, product, _no_real_email
):
    _order, return_id = _delivered_order_with_items(
        db_session, client, customer, customer_headers, product
    )

    response = client.post(
        f"/admin/returns/{return_id}/reject", json={"comment": "No."}, headers=admin_headers
    )
    assert response.status_code == 200

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert not any(n["type"] == "return_approved" for n in notifications["items"])

    approved_emails = [e for e in _no_real_email if "Return request approved" in e["subject"]]
    assert len(approved_emails) == 0
