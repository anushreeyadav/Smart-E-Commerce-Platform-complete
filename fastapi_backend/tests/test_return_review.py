from datetime import datetime, timedelta, timezone

from app.models.order import Order, OrderStatus
from app.models.return_request import ReturnRequestStatus


def _delivered_order_with_return(db_session, client, customer, customer_headers):
    order = Order(
        user_id=customer.id,
        status=OrderStatus.DELIVERED,
        total_amount=25,
        delivered_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    response = client.post(
        f"/orders/{order.id}/return",
        json={"reason": "Item arrived damaged", "comment": "Corner is cracked."},
        headers=customer_headers,
    )
    assert response.status_code == 201
    return order


def test_staff_can_approve_return_request(
    db_session, client, customer, customer_headers, staff_headers, staff_user
):
    order = _delivered_order_with_return(db_session, client, customer, customer_headers)

    response = client.post(
        f"/orders/{order.id}/return/approve",
        json={"comment": "Approved, refund issued."},
        headers=staff_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["reviewed_by"] == staff_user.id
    assert body["reviewed_by_name"] == staff_user.name
    assert body["review_comment"] == "Approved, refund issued."
    # original customer submission is preserved
    assert body["reason"] == "Item arrived damaged"
    assert body["comments"] == "Corner is cracked."

    statuses = [entry["new_status"] for entry in body["history"]]
    assert statuses == ["pending", "approved"]

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert any(n["type"] == "return_approved" for n in notifications["items"])


def test_staff_can_reject_return_request_with_required_comment(
    db_session, client, customer, customer_headers, staff_headers, staff_user
):
    order = _delivered_order_with_return(db_session, client, customer, customer_headers)

    missing_comment = client.post(
        f"/orders/{order.id}/return/reject",
        json={},
        headers=staff_headers,
    )
    assert missing_comment.status_code == 422

    response = client.post(
        f"/orders/{order.id}/return/reject",
        json={"comment": "Item shows signs of misuse, not covered."},
        headers=staff_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["review_comment"] == "Item shows signs of misuse, not covered."
    assert body["reason"] == "Item arrived damaged"

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert any(n["type"] == "return_rejected" for n in notifications["items"])


def test_finalized_return_request_cannot_be_processed_again(
    db_session, client, customer, customer_headers, staff_headers
):
    order = _delivered_order_with_return(db_session, client, customer, customer_headers)

    first = client.post(
        f"/orders/{order.id}/return/approve",
        json={},
        headers=staff_headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/orders/{order.id}/return/reject",
        json={"comment": "changed my mind"},
        headers=staff_headers,
    )
    assert second.status_code == 400


def test_customer_cannot_approve_or_reject_return_requests(
    db_session, client, customer, customer_headers
):
    order = _delivered_order_with_return(db_session, client, customer, customer_headers)

    approve = client.post(
        f"/orders/{order.id}/return/approve",
        json={},
        headers=customer_headers,
    )
    assert approve.status_code == 403

    reject = client.post(
        f"/orders/{order.id}/return/reject",
        json={"comment": "no"},
        headers=customer_headers,
    )
    assert reject.status_code == 403


def test_approve_return_for_order_without_request_returns_404(
    db_session, client, customer, staff_headers
):
    order = Order(
        user_id=customer.id,
        status=OrderStatus.DELIVERED,
        total_amount=10,
        delivered_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    response = client.post(
        f"/orders/{order.id}/return/approve",
        json={},
        headers=staff_headers,
    )
    assert response.status_code == 404
