from datetime import datetime, timezone

from app.models.order import Order, OrderStatus


def _delivered_order_with_return(db_session, client, customer, customer_headers, *, reason="Item arrived damaged"):
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
        json={"reason": reason, "comment": "Corner is cracked."},
        headers=customer_headers,
    )
    assert response.status_code == 201
    return order, response.json()["id"]


def test_admin_can_list_return_requests(
    db_session, client, customer, customer_headers, admin_headers
):
    order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)

    response = client.get("/admin/returns", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == return_id
    assert body["items"][0]["order_id"] == order.id
    assert body["items"][0]["status"] == "pending"


def test_staff_can_list_return_requests(
    db_session, client, customer, customer_headers, staff_headers
):
    _delivered_order_with_return(db_session, client, customer, customer_headers)

    response = client.get("/admin/returns", headers=staff_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_customer_cannot_list_return_requests(
    db_session, client, customer, customer_headers
):
    _delivered_order_with_return(db_session, client, customer, customer_headers)

    response = client.get("/admin/returns", headers=customer_headers)
    assert response.status_code == 403


def test_unauthenticated_cannot_list_return_requests(client):
    response = client.get("/admin/returns")
    assert response.status_code in (401, 403)


def test_list_return_requests_filters_by_status(
    db_session, client, customer, other_customer, customer_headers, other_customer_headers, admin_headers
):
    _order_a, return_id_a = _delivered_order_with_return(
        db_session, client, customer, customer_headers, reason="Damaged item"
    )
    _order_b, return_id_b = _delivered_order_with_return(
        db_session, client, other_customer, other_customer_headers, reason="Wrong item"
    )

    approve = client.post(
        f"/admin/returns/{return_id_a}/approve",
        json={"comment": "Approved."},
        headers=admin_headers,
    )
    assert approve.status_code == 200

    pending_only = client.get(
        "/admin/returns", params={"status": "pending"}, headers=admin_headers
    )
    assert pending_only.status_code == 200
    pending_ids = [item["id"] for item in pending_only.json()["items"]]
    assert pending_ids == [return_id_b]

    approved_only = client.get(
        "/admin/returns", params={"status": "approved"}, headers=admin_headers
    )
    assert approved_only.status_code == 200
    approved_ids = [item["id"] for item in approved_only.json()["items"]]
    assert approved_ids == [return_id_a]


def test_list_return_requests_invalid_status_returns_422(
    db_session, client, customer, customer_headers, admin_headers
):
    _delivered_order_with_return(db_session, client, customer, customer_headers)

    response = client.get(
        "/admin/returns", params={"status": "not-a-status"}, headers=admin_headers
    )
    assert response.status_code == 422


def test_admin_can_approve_return_request_by_id(
    db_session, client, customer, customer_headers, admin_headers, admin_user
):
    _order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)

    response = client.post(
        f"/admin/returns/{return_id}/approve",
        json={"comment": "Approved, refund issued."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["reviewed_by"] == admin_user.id
    assert body["review_comment"] == "Approved, refund issued."
    assert body["reason"] == "Item arrived damaged"

    statuses = [entry["new_status"] for entry in body["history"]]
    assert statuses == ["pending", "approved"]

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert any(n["type"] == "return_approved" for n in notifications["items"])


def test_admin_can_reject_return_request_with_required_comment(
    db_session, client, customer, customer_headers, admin_headers, admin_user
):
    _order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)

    missing_comment = client.post(
        f"/admin/returns/{return_id}/reject",
        json={},
        headers=admin_headers,
    )
    assert missing_comment.status_code == 422

    blank_comment = client.post(
        f"/admin/returns/{return_id}/reject",
        json={"comment": "   "},
        headers=admin_headers,
    )
    assert blank_comment.status_code == 422

    response = client.post(
        f"/admin/returns/{return_id}/reject",
        json={"comment": "Item shows signs of misuse, not covered."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["reviewed_by"] == admin_user.id
    assert body["review_comment"] == "Item shows signs of misuse, not covered."

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert any(n["type"] == "return_rejected" for n in notifications["items"])


def test_reviewing_already_finalized_return_request_returns_400(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)

    first = client.post(
        f"/admin/returns/{return_id}/approve",
        json={},
        headers=admin_headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/admin/returns/{return_id}/reject",
        json={"comment": "changed my mind"},
        headers=admin_headers,
    )
    assert second.status_code == 400


def test_customer_cannot_approve_or_reject_via_admin_endpoint(
    db_session, client, customer, customer_headers
):
    _order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)

    approve = client.post(
        f"/admin/returns/{return_id}/approve",
        json={},
        headers=customer_headers,
    )
    assert approve.status_code == 403

    reject = client.post(
        f"/admin/returns/{return_id}/reject",
        json={"comment": "no"},
        headers=customer_headers,
    )
    assert reject.status_code == 403


def test_unauthenticated_cannot_approve_or_reject(
    db_session, client, customer, customer_headers
):
    _order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)

    approve = client.post(f"/admin/returns/{return_id}/approve", json={})
    assert approve.status_code in (401, 403)

    reject = client.post(f"/admin/returns/{return_id}/reject", json={"comment": "no"})
    assert reject.status_code in (401, 403)


def test_approve_nonexistent_return_request_returns_404(client, admin_headers):
    response = client.post(
        "/admin/returns/does-not-exist/approve",
        json={},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_reject_nonexistent_return_request_returns_404(client, admin_headers):
    response = client.post(
        "/admin/returns/does-not-exist/reject",
        json={"comment": "no such request"},
        headers=admin_headers,
    )
    assert response.status_code == 404
