from datetime import datetime, timedelta, timezone

from app.models.order import Order, OrderStatus
from app.models.return_request import ReturnRequest, ReturnRequestStatus


def _delivered_order(db_session, user_id, delivered_at=None):
    order = Order(
        user_id=user_id,
        status=OrderStatus.DELIVERED,
        total_amount=25,
        delivered_at=delivered_at or datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


def test_customer_can_request_return_for_recently_delivered_order(
    client, db_session, customer, customer_headers
):
    order = _delivered_order(db_session, customer.id)

    response = client.post(
        f"/orders/{order.id}/return",
        json={"reason": "Item arrived damaged", "comment": "Corner is cracked."},
        headers=customer_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["order_id"] == order.id
    assert body["user_id"] == customer.id
    assert body["reason"] == "Item arrived damaged"
    assert body["comments"] == "Corner is cracked."
    assert body["status"] == "pending"

    stored_request = db_session.query(ReturnRequest).filter_by(id=body["id"]).one()
    assert stored_request.status == ReturnRequestStatus.PENDING
    assert stored_request.order.id == order.id
    assert stored_request.user.id == customer.id
    db_session.refresh(order)
    assert order.status == OrderStatus.RETURN_REQUESTED

    orders = client.get("/orders/me", headers=customer_headers).json()
    assert orders[0]["status"] == "return_requested"
    assert orders[0]["return_eligible"] is False
    assert orders[0]["return_request"]["id"] == body["id"]


def test_return_request_rejects_duplicate_and_other_users_order(
    client, db_session, customer, customer_headers, other_customer_headers
):
    order = _delivered_order(db_session, customer.id)

    forbidden = client.post(
        f"/orders/{order.id}/return",
        json={"reason": "Wrong size"},
        headers=other_customer_headers,
    )
    assert forbidden.status_code == 403

    first = client.post(
        f"/orders/{order.id}/return",
        json={"reason": "Wrong size"},
        headers=customer_headers,
    )
    assert first.status_code == 201

    duplicate = client.post(
        f"/orders/{order.id}/return",
        json={"reason": "Changed my mind"},
        headers=customer_headers,
    )
    assert duplicate.status_code == 409


def test_return_request_requires_delivered_order_within_window(
    client, db_session, customer, customer_headers
):
    expired_order = _delivered_order(
        db_session,
        customer.id,
        datetime.now(timezone.utc) - timedelta(days=8),
    )
    expired = client.post(
        f"/orders/{expired_order.id}/return",
        json={"reason": "No longer needed"},
        headers=customer_headers,
    )
    assert expired.status_code == 400
    assert expired.json()["detail"] == "The return window has expired"

    undelivered = Order(user_id=customer.id, status=OrderStatus.SHIPPED, total_amount=25)
    db_session.add(undelivered)
    db_session.commit()

    invalid_status = client.post(
        f"/orders/{undelivered.id}/return",
        json={"reason": "No longer needed"},
        headers=customer_headers,
    )
    assert invalid_status.status_code == 400
    assert invalid_status.json()["detail"] == "Only delivered orders can be returned"
