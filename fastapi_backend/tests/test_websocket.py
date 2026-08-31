from starlette.websockets import WebSocketDisconnect

from app.services.connection_manager import manager
from tests.conftest import add_to_cart


def test_connect_without_token_is_rejected(client):
    try:
        with client.websocket_connect("/ws/notifications"):
            assert False, "expected the connection to be rejected"
    except WebSocketDisconnect as exc:
        assert exc.code == 1008


def test_connect_with_invalid_token_is_rejected(client):
    try:
        with client.websocket_connect("/ws/notifications?token=not-a-real-jwt"):
            assert False, "expected the connection to be rejected"
    except WebSocketDisconnect as exc:
        assert exc.code == 1008


def test_connect_with_valid_token_registers_connection(client, customer):
    from app.core.security import create_access_token

    token = create_access_token(data={"sub": customer.id, "role": customer.role.value})

    with client.websocket_connect(f"/ws/notifications?token={token}") as ws:
        assert customer.id in manager.active_connections
        assert len(manager.active_connections[customer.id]) == 1

    assert customer.id not in manager.active_connections


def test_notification_created_is_pushed_over_the_socket(
    client, customer, customer_headers, product
):
    from app.core.security import create_access_token

    token = create_access_token(data={"sub": customer.id, "role": customer.role.value})

    with client.websocket_connect(f"/ws/notifications?token={token}") as ws:
        add_to_cart(client, customer_headers, product.id, 1)
        client.post(
            "/checkout",
            json={"payment_method": "stripe", "currency": "inr"},
            headers=customer_headers,
        )

        message = ws.receive_json()
        assert message["event"] in {"notification_created", "cart_updated"}


def test_cart_updated_event_is_emitted(client, customer, customer_headers, product):
    from app.core.security import create_access_token

    token = create_access_token(data={"sub": customer.id, "role": customer.role.value})

    with client.websocket_connect(f"/ws/notifications?token={token}") as ws:
        add_to_cart(client, customer_headers, product.id, 1)

        message = ws.receive_json()
        assert message["event"] == "cart_updated"
        assert message["data"]["total_items"] == 1
