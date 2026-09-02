import os
import tempfile
import uuid

import pytest

_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"smart_test_{uuid.uuid4().hex}.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("AUTH0_DOMAIN", "test.auth0.com")
os.environ.setdefault("AUTH0_AUDIENCE", "https://smart-ecommerce-api")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.pop("SMTP_HOST", None)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.db.database import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
import app.services.email_service as email_service  # noqa: E402


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _clean_database():
    yield

    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture(autouse=True)
def _no_real_email(monkeypatch):
    sent = []

    def fake_send_email(*, recipient, subject, body):
        sent.append({"recipient": recipient, "subject": subject, "body": body})
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send_email)
    return sent


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


def _create_user(db_session, *, role: UserRole, email: str | None = None) -> User:
    email = email or f"{role.value}-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        name=f"Test {role.value.title()}",
        email=email,
        password=hash_password("Password@123"),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": user.id, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def customer(db_session):
    return _create_user(db_session, role=UserRole.CUSTOMER)


@pytest.fixture
def other_customer(db_session):
    return _create_user(db_session, role=UserRole.CUSTOMER)


@pytest.fixture
def staff_user(db_session):
    return _create_user(db_session, role=UserRole.STAFF)


@pytest.fixture
def admin_user(db_session):
    return _create_user(db_session, role=UserRole.ADMIN)


@pytest.fixture
def customer_headers(customer):
    return _auth_headers(customer)


@pytest.fixture
def other_customer_headers(other_customer):
    return _auth_headers(other_customer)


@pytest.fixture
def staff_headers(staff_user):
    return _auth_headers(staff_user)


@pytest.fixture
def admin_headers(admin_user):
    return _auth_headers(admin_user)


@pytest.fixture
def product(db_session):
    item = Product(
        name="Test Widget",
        description="A widget for testing.",
        category="general",
        price=100,
        stock=25,
        images=[],
        popularity=10,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


class FakePaymentIntent:
    def __init__(self, id_: str):
        self.id = id_
        self.client_secret = f"{id_}_secret"


class FakeStripeObject:
    """Mimics the real (non-dict) stripe-python StripeObject just enough to
    catch code that calls .get() on a Stripe response instead of using
    bracket access / stripe_field(). stripe-python 15.x's StripeObject
    raises AttributeError on .get() ("is not a dict"), but a plain dict
    stand-in would let that exact bug slip through every test - so this
    fake deliberately doesn't implement .get() either."""

    def __init__(self, data: dict):
        self._data = {
            key: FakeStripeObject(value) if isinstance(value, dict) else value
            for key, value in data.items()
        }

    def __getitem__(self, key):
        return self._data[key]

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __contains__(self, key):
        return key in self._data

    def __repr__(self):
        return f"FakeStripeObject({self._data!r})"


class FakeCheckoutSession:
    def __init__(self, id_: str):
        self.id = id_
        self.url = f"https://stripe.test/checkout/{id_}"


class FakeCheckoutSessionApi:
    # Keyed by session id, so tests can control what `retrieve` reports back
    # (simulating what a real Stripe Checkout Session would look like after
    # the customer pays, abandons, or the session expires).
    sessions: dict = {}

    @classmethod
    def create(cls, **kwargs):
        session = FakeCheckoutSession(f"cs_test_{uuid.uuid4().hex[:12]}")
        cls.sessions[session.id] = {
            "id": session.id,
            "status": "open",
            "payment_status": "unpaid",
            "payment_intent": None,
        }
        return session

    @classmethod
    def retrieve(cls, session_id, **kwargs):
        return FakeStripeObject(
            cls.sessions.get(
                session_id,
                {
                    "id": session_id,
                    "status": "open",
                    "payment_status": "unpaid",
                    "payment_intent": None,
                },
            )
        )


class FakePaymentIntentApi:
    @staticmethod
    def create(**kwargs):
        return FakePaymentIntent(f"pi_test_{uuid.uuid4().hex[:12]}")


class FakeSignatureVerificationError(Exception):
    pass


class FakeWebhookApi:
    @staticmethod
    def construct_event(*, payload, sig_header, secret):
        import json

        return FakeStripeObject(json.loads(payload))


class FakeStripeError:
    SignatureVerificationError = FakeSignatureVerificationError


class FakeRefund:
    def __init__(self, id_: str, payment_intent: str):
        self.id = id_
        self.payment_intent = payment_intent
        self.status = "succeeded"


class FakeRefundApi:
    calls = []
    created = []

    @classmethod
    def create(cls, **kwargs):
        cls.calls.append(kwargs)
        refund = FakeRefund(f"re_test_{uuid.uuid4().hex[:12]}", kwargs.get("payment_intent"))
        cls.created.append(refund)
        return refund


class FakeStripe:
    PaymentIntent = FakePaymentIntentApi
    checkout = type("checkout", (), {"Session": FakeCheckoutSessionApi})
    Webhook = FakeWebhookApi
    Refund = FakeRefundApi
    error = FakeStripeError


@pytest.fixture(autouse=True)
def _fake_stripe(monkeypatch):
    FakeRefundApi.calls = []
    FakeRefundApi.created = []
    FakeCheckoutSessionApi.sessions = {}
    fake = FakeStripe()
    monkeypatch.setattr(
        "app.services.order_service.get_stripe_client", lambda: fake
    )
    monkeypatch.setattr("app.services.return_service.get_stripe_client", lambda: fake)
    monkeypatch.setattr("app.api.webhooks.get_stripe_client", lambda: fake)
    return fake


def add_to_cart(client, headers, product_id, quantity=1):
    return client.post(
        "/cart/add",
        json={"product_id": product_id, "quantity": quantity},
        headers=headers,
    )
