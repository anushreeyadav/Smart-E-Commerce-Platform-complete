import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import Base, engine

# Import models so SQLAlchemy knows about them
from app.models import User, Product, Cart
from app.api.notifications import router as notifications_router

# Import routers
from app.api.auth import router as auth_router
from app.api.rbac import router as rbac_router
from app.api.products import router as products_router
from app.api.cart import router as cart_router
from app.api.checkout import router as checkout_router
from app.api.orders import router as orders_router
from app.api.admin_returns import router as admin_returns_router
from app.api.payments import router as payments_router
from app.api.webhooks import router as webhooks_router
from app.api.websocket import router as websocket_router


# ---------------------------------------------------------
# Create database tables
# ---------------------------------------------------------

Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="Smart E-Commerce API",
    description="FastAPI backend for Smart E-Commerce Platform",
    version="1.0.0",
)

app.state.stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            ",".join(
                filter(
                    None,
                    [
                        os.getenv("FRONTEND_URL", "http://localhost:3000"),
                        "http://127.0.0.1:3000",
                    ],
                )
            ),
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------

app.include_router(
    auth_router,
    tags=["Authentication"],
)

app.include_router(
    rbac_router,
    prefix="/rbac",
    tags=["Role-Based Access Control"],
)

app.include_router(
    products_router,
    prefix="/products",
    tags=["Products"],
)

app.include_router(
    cart_router,
    prefix="/cart",
    tags=["Cart"],
)

app.include_router(
    checkout_router,
    tags=["Checkout"],
)

app.include_router(
    orders_router,
    tags=["Orders"],
)

app.include_router(
    admin_returns_router,
    tags=["Admin - Returns"],
)

app.include_router(
    payments_router,
    tags=["Payments"],
)

app.include_router(
    webhooks_router,
    tags=["Webhooks"],
)
app.include_router(
    notifications_router,
    tags=["Notifications"],
)
app.include_router(websocket_router)


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Smart E-Commerce API is running"
    }


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
