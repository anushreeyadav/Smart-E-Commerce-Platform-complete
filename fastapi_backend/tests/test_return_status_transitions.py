from datetime import datetime, timezone

import pytest

from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus


def _delivered_order_with_return(db_session, client, customer, customer_headers, *, with_payment=True):
    order = Order(
        user_id=customer.id,
        status=OrderStatus.DELIVERED,
        payment_status=PaymentStatus.PAID.value if with_payment else PaymentStatus.PENDING.value,
        total_amount=25,
        delivered_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

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


def _approved_return(db_session, client, customer, customer_headers, admin_headers, **kwargs):
    order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers, **kwargs)
    response = client.post(
        f"/admin/returns/{return_id}/approve",
        json={"comment": "Approved."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    return order, return_id


def _returned_return(db_session, client, customer, customer_headers, admin_headers, **kwargs):
    order, return_id = _approved_return(db_session, client, customer, customer_headers, admin_headers, **kwargs)
    response = client.post(
        f"/admin/returns/{return_id}/mark-returned",
        json={},
        headers=admin_headers,
    )
    assert response.status_code == 200
    return order, return_id


# ---------------------------------------------------------------------------
# Valid transitions
# ---------------------------------------------------------------------------


def test_pending_can_transition_to_approved(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)

    response = client.post(
        f"/admin/returns/{return_id}/approve",
        json={"comment": "Approved."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_pending_can_transition_to_rejected(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)

    response = client.post(
        f"/admin/returns/{return_id}/reject",
        json={"comment": "Not eligible."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_approved_can_transition_to_returned(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _approved_return(db_session, client, customer, customer_headers, admin_headers)

    response = client.post(
        f"/admin/returns/{return_id}/mark-returned",
        json={"comment": "Item received back at warehouse."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "returned"
    statuses = [entry["new_status"] for entry in body["history"]]
    assert statuses == ["pending", "approved", "returned"]


def test_returned_can_transition_to_refunded(
    db_session, client, customer, customer_headers, admin_headers
):
    order, return_id = _returned_return(db_session, client, customer, customer_headers, admin_headers)

    response = client.post(
        f"/admin/returns/{return_id}/refund",
        json={"comment": "Refund issued to original payment method."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "refunded"
    statuses = [entry["new_status"] for entry in body["history"]]
    assert statuses == ["pending", "approved", "returned", "refunded"]

    order_detail = client.get(f"/orders/{order.id}", headers=admin_headers).json()
    assert order_detail["payment_status"] == "refunded"


def test_approved_can_initiate_refund_directly(
    db_session, client, customer, customer_headers, admin_headers, _fake_stripe
):
    """The admin doesn't have to call mark-returned first: initiating a
    refund on an approved request auto-records the 'returned' step and
    actually calls Stripe to refund the payment."""

    order, return_id = _approved_return(db_session, client, customer, customer_headers, admin_headers)

    response = client.post(
        f"/admin/returns/{return_id}/refund",
        json={"comment": "Refund issued to original payment method."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "refunded"
    statuses = [entry["new_status"] for entry in body["history"]]
    assert statuses == ["pending", "approved", "returned", "refunded"]

    assert len(_fake_stripe.Refund.calls) == 1
    assert _fake_stripe.Refund.calls[0]["payment_intent"] == f"pi_test_{order.id[:8]}"

    order_detail = client.get(f"/orders/{order.id}", headers=admin_headers).json()
    assert order_detail["payment_status"] == "refunded"

    notifications = client.get("/notifications", headers=customer_headers).json()
    assert any(n["type"] == "refund_processed" for n in notifications["items"])


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "endpoint",
    ["mark-returned", "refund"],
)
def test_pending_cannot_skip_ahead(
    db_session, client, customer, customer_headers, admin_headers, endpoint
):
    _order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)

    response = client.post(
        f"/admin/returns/{return_id}/{endpoint}",
        json={},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_approved_cannot_be_rejected(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _approved_return(db_session, client, customer, customer_headers, admin_headers)

    response = client.post(
        f"/admin/returns/{return_id}/reject",
        json={"comment": "changed my mind"},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_rejected_is_terminal(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)
    reject = client.post(
        f"/admin/returns/{return_id}/reject",
        json={"comment": "Not eligible."},
        headers=admin_headers,
    )
    assert reject.status_code == 200

    for endpoint, body in [
        ("approve", {}),
        ("mark-returned", {}),
        ("refund", {}),
    ]:
        response = client.post(
            f"/admin/returns/{return_id}/{endpoint}",
            json=body,
            headers=admin_headers,
        )
        assert response.status_code == 400


def test_refunded_is_terminal(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _returned_return(db_session, client, customer, customer_headers, admin_headers)
    refund = client.post(
        f"/admin/returns/{return_id}/refund",
        json={},
        headers=admin_headers,
    )
    assert refund.status_code == 200

    for endpoint, body in [
        ("approve", {}),
        ("mark-returned", {}),
        ("refund", {}),
    ]:
        response = client.post(
            f"/admin/returns/{return_id}/{endpoint}",
            json=body,
            headers=admin_headers,
        )
        assert response.status_code == 400


def test_duplicate_status_update_is_rejected(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _approved_return(db_session, client, customer, customer_headers, admin_headers)

    response = client.post(
        f"/admin/returns/{return_id}/approve",
        json={"comment": "approve again"},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_returned_cannot_go_backwards_to_approved(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _returned_return(db_session, client, customer, customer_headers, admin_headers)

    response = client.post(
        f"/admin/returns/{return_id}/approve",
        json={},
        headers=admin_headers,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Refund-specific validation
# ---------------------------------------------------------------------------


def test_refund_requires_a_completed_payment(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _approved_return(
        db_session, client, customer, customer_headers, admin_headers, with_payment=False
    )

    response = client.post(
        f"/admin/returns/{return_id}/refund",
        json={},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_refund_failure_from_stripe_returns_502_and_preserves_partial_progress(
    db_session, client, customer, customer_headers, admin_headers, _fake_stripe, monkeypatch
):
    _order, return_id = _approved_return(db_session, client, customer, customer_headers, admin_headers)

    def _boom(**_kwargs):
        raise RuntimeError("stripe outage")

    monkeypatch.setattr(_fake_stripe.Refund, "create", _boom)

    response = client.post(
        f"/admin/returns/{return_id}/refund",
        json={},
        headers=admin_headers,
    )
    assert response.status_code == 502

    # The auto "mark returned" step still committed even though the
    # subsequent Stripe call failed, so a retry only needs to redo the refund.
    listing = client.get("/admin/returns", params={"status": "returned"}, headers=admin_headers)
    ids = [item["id"] for item in listing.json()["items"]]
    assert ids == [return_id]


# ---------------------------------------------------------------------------
# Existence checks / misc
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("endpoint", ["approve", "reject", "mark-returned", "refund"])
def test_transition_on_nonexistent_return_request_returns_404(client, admin_headers, endpoint):
    body = {"comment": "n/a"} if endpoint in ("reject",) else {}
    response = client.post(
        f"/admin/returns/does-not-exist/{endpoint}",
        json=body,
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_successful_transition_persists_and_is_returned_in_response(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _approved_return(db_session, client, customer, customer_headers, admin_headers)

    response = client.post(
        f"/admin/returns/{return_id}/mark-returned",
        json={},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "returned"

    listing = client.get("/admin/returns", params={"status": "returned"}, headers=admin_headers)
    assert listing.status_code == 200
    ids = [item["id"] for item in listing.json()["items"]]
    assert ids == [return_id]


def test_failed_transition_does_not_change_status(
    db_session, client, customer, customer_headers, admin_headers
):
    _order, return_id = _delivered_order_with_return(db_session, client, customer, customer_headers)

    failed = client.post(
        f"/admin/returns/{return_id}/refund",
        json={},
        headers=admin_headers,
    )
    assert failed.status_code == 400

    listing = client.get("/admin/returns", params={"status": "pending"}, headers=admin_headers)
    assert listing.status_code == 200
    ids = [item["id"] for item in listing.json()["items"]]
    assert ids == [return_id]
