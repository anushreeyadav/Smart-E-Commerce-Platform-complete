from datetime import datetime, timezone

from app.models.order import Order, OrderStatus


def _order(db_session, user_id, status=OrderStatus.PAID, total=100):
    order = Order(user_id=user_id, status=status, total_amount=total)
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


def test_customer_cannot_list_admin_orders(client, customer_headers):
    response = client.get("/orders", headers=customer_headers)
    assert response.status_code == 403


def test_admin_can_list_and_filter_orders(
    db_session, client, customer, staff_headers
):
    _order(db_session, customer.id, status=OrderStatus.PAID, total=50)
    _order(db_session, customer.id, status=OrderStatus.SHIPPED, total=75)

    response = client.get("/orders", headers=staff_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 2
    assert body["page"] == 1
    first = body["items"][0]
    assert "customer_name" in first
    assert "customer_email" in first
    assert first["customer_email"] == customer.email

    filtered = client.get("/orders?status=shipped", headers=staff_headers)
    assert filtered.status_code == 200
    assert all(item["status"] == "shipped" for item in filtered.json()["items"])

    searched = client.get(f"/orders?search={customer.email}", headers=staff_headers)
    assert searched.status_code == 200
    assert searched.json()["total"] >= 2


def test_order_status_transition_via_out_for_delivery(
    db_session, client, customer, staff_headers
):
    order = _order(db_session, customer.id, status=OrderStatus.SHIPPED)

    out_for_delivery = client.patch(
        f"/orders/{order.id}/status",
        json={"status": "out_for_delivery"},
        headers=staff_headers,
    )
    assert out_for_delivery.status_code == 200
    assert out_for_delivery.json()["status"] == "out_for_delivery"

    delivered = client.patch(
        f"/orders/{order.id}/status",
        json={"status": "delivered"},
        headers=staff_headers,
    )
    assert delivered.status_code == 200
    body = delivered.json()
    assert body["status"] == "delivered"

    history = body["status_history"]
    new_statuses = [entry["new_status"] for entry in history]
    assert "out_for_delivery" in new_statuses
    assert "delivered" in new_statuses
    # every admin-driven entry records who made the change
    delivered_entry = next(e for e in history if e["new_status"] == "delivered")
    assert delivered_entry["changed_by"] is not None


def test_shipped_to_delivered_direct_transition_still_allowed(
    db_session, client, customer, admin_headers
):
    order = _order(db_session, customer.id, status=OrderStatus.SHIPPED)

    response = client.patch(
        f"/orders/{order.id}/status",
        json={"status": "delivered"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"


def test_admin_cannot_manually_mark_an_order_paid(
    db_session, client, customer, admin_headers, staff_headers
):
    """An order can only become 'paid' through a real, Stripe-verified
    payment (webhook or the Confirm Payment sync) - never a manual status
    click, which used to let an order (and its "Payment" column) show PAID
    without any money ever actually changing hands."""

    order = _order(db_session, customer.id, status=OrderStatus.CONFIRMED)

    response = client.patch(
        f"/orders/{order.id}/status",
        json={"status": "paid"},
        headers=admin_headers,
    )
    assert response.status_code == 400

    db_session.refresh(order)
    assert order.status == OrderStatus.CONFIRMED
    assert order.payment_status == "pending"

    # Also blocked for staff, and regardless of the order's current status.
    other_order = _order(db_session, customer.id, status=OrderStatus.PENDING)
    staff_response = client.patch(
        f"/orders/{other_order.id}/status",
        json={"status": "paid"},
        headers=staff_headers,
    )
    assert staff_response.status_code == 400


def test_order_detail_includes_shipping_address_and_history(
    db_session, client, customer, customer_headers
):
    order = Order(
        user_id=customer.id,
        status=OrderStatus.CONFIRMED,
        total_amount=20,
        shipping_address="221B Baker Street",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    response = client.get(f"/orders/{order.id}", headers=customer_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["shipping_address"] == "221B Baker Street"
    assert body["status_history"] == []  # created directly, not via checkout
