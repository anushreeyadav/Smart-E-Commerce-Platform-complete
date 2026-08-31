from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.services import email_service


def _fake_user():
    return User(
        id="user-1", name="Jane Doe", email="jane@example.com", role=UserRole.CUSTOMER
    )


def _fake_order(status=OrderStatus.CONFIRMED):
    return Order(
        id="order-1",
        user_id="user-1",
        status=status,
        payment_status="pending",
        total_amount=49.99,
        payment_method="stripe",
        currency="inr",
    )


def test_order_confirmation_email_uses_correct_template(monkeypatch):
    captured = {}

    def fake_send_email(*, recipient, subject, body):
        captured["recipient"] = recipient
        captured["subject"] = subject
        captured["body"] = body
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send_email)

    email_service.send_order_confirmation_email(_fake_user(), _fake_order())

    assert captured["recipient"] == "jane@example.com"
    assert "Order confirmed" in captured["subject"]
    assert "order-1" in captured["body"]
    assert "Jane Doe" in captured["body"]


def test_payment_failed_email_uses_correct_template(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda **kwargs: captured.update(kwargs) or True,
    )

    email_service.send_payment_failed_email(_fake_user(), _fake_order())

    assert "Payment failed" in captured["subject"]


def test_order_shipped_and_delivered_use_different_templates(monkeypatch):
    subjects = []
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda **kwargs: subjects.append(kwargs["subject"]) or True,
    )

    email_service.send_order_shipped_email(_fake_user(), _fake_order(OrderStatus.SHIPPED))
    email_service.send_order_delivered_email(_fake_user(), _fake_order(OrderStatus.DELIVERED))

    assert "shipped" in subjects[0].lower()
    assert "delivered" in subjects[1].lower()


def test_send_email_with_retry_succeeds_after_transient_failures(monkeypatch):
    attempts = {"count": 0}

    def flaky_send(*, recipient, subject, body):
        attempts["count"] += 1
        return attempts["count"] >= 3

    monkeypatch.setattr(email_service, "send_email", flaky_send)
    monkeypatch.setattr(email_service.time, "sleep", lambda *_: None)

    result = email_service.send_email_with_retry(
        recipient="a@example.com",
        subject="Test",
        body="Body",
        max_attempts=3,
        base_delay=0.01,
    )

    assert result is True
    assert attempts["count"] == 3


def test_send_email_with_retry_gives_up_after_max_attempts(monkeypatch):
    attempts = {"count": 0}

    def always_fails(*, recipient, subject, body):
        attempts["count"] += 1
        return False

    monkeypatch.setattr(email_service, "send_email", always_fails)
    monkeypatch.setattr(email_service.time, "sleep", lambda *_: None)

    result = email_service.send_email_with_retry(
        recipient="a@example.com",
        subject="Test",
        body="Body",
        max_attempts=3,
        base_delay=0.01,
    )

    assert result is False
    assert attempts["count"] == 3
