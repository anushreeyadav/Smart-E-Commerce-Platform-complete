# Smart E-Commerce Assignment

Full-stack assignment project with:

- `fastapi_backend/` for APIs, auth, cart, orders, payments, and RBAC
- `django_admin/` for analytics/admin dashboard
- `frontend/` for the Next.js storefront and Auth0 social login
- `postman/` for API testing collection

## Project Structure

```text
smart-ecommerce/
├── fastapi_backend/
├── django_admin/
├── frontend/
├── postman/
├── README.md
└── SUBMISSION.md
```

## Implemented Features

- FastAPI authentication
  - email/password login
  - JWT access token
  - JWT refresh token
  - password hashing
- Auth0 social login
  - Google login
  - Facebook login support configured in Auth0
- Role-based access control
  - admin
  - staff
  - customer
- Commerce APIs
  - cart
  - checkout
  - orders
  - payments
- Database models
  - user
  - product
  - cart
  - order
  - payment
- Django analytics dashboard
  - user counts
  - product counts
  - cart counts
  - order counts
  - revenue tracking
  - Chart.js trends, stock, order, payment, and user metrics
  - protected CSV/PDF reports
- Next.js frontend
  - storefront home page
  - products page
  - cart page
  - Auth0 login flow

## Demo Credentials

Use these local credentials for FastAPI login:

- Admin
  - Email: `admin@example.com`
  - Password: `Admin@12345`
- Staff
  - Email: `staff@example.com`
  - Password: `Staff@12345`
- Customer
  - Email: `customer@example.com`
  - Password: `Customer@12345`

## Key URLs

- FastAPI API: `http://127.0.0.1:8000`
- FastAPI Swagger docs: `http://127.0.0.1:8000/docs`
- Next.js frontend: `http://localhost:3000`
- Django dashboard: `http://localhost:8080/dashboard/`
- Django admin: `http://localhost:8080/admin/`
- API reference: [`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md)

## Environment Setup

### `fastapi_backend/.env`

Use your own values for secrets and Auth0 settings.

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/smartdb
JWT_SECRET_KEY=change-this-to-a-long-random-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

AUTH0_DOMAIN=<your-auth0-domain>
AUTH0_CLIENT_ID=<your-auth0-client-id>
AUTH0_CLIENT_SECRET=<your-auth0-client-secret>
AUTH0_AUDIENCE=<your-auth0-api-audience>

FRONTEND_URL=http://localhost:3000
STRIPE_SECRET_KEY=<your-stripe-secret-key>
STRIPE_WEBHOOK_SECRET=<your-stripe-webhook-secret>
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### `frontend/.env.local`

```env
AUTH0_DOMAIN=<your-auth0-domain>
AUTH0_CLIENT_ID=<your-auth0-client-id>
AUTH0_CLIENT_SECRET=<your-auth0-client-secret>
AUTH0_SECRET=<your-long-random-secret>
AUTH0_AUDIENCE=<your-auth0-api-audience>
APP_BASE_URL=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Auth0 Setup

In Auth0 Application Settings, configure:

- Allowed Callback URLs
  - `http://localhost:3000/auth/callback`
- Allowed Logout URLs
  - `http://localhost:3000`
- Allowed Web Origins
  - `http://localhost:3000`
- Allowed Origins (CORS)
  - `http://localhost:3000`

For social login:

- Enable Google and/or Facebook in the Auth0 dashboard
- Connect the provider to the application
- Add the Auth0 callback URL to the provider settings if required

## Stripe Setup

For checkout and payment processing:

- Install backend dependencies
  - `cd fastapi_backend`
  - `pip install -r requirements.txt`
- Add Stripe secrets to `fastapi_backend/.env`
  - `STRIPE_SECRET_KEY`
  - `STRIPE_WEBHOOK_SECRET`
- Configure the Stripe webhook endpoint
  - `POST http://127.0.0.1:8000/webhooks/stripe`
- Send Stripe events for:
  - `checkout.session.completed`
  - `payment_intent.succeeded`

If you are using a local or existing database, apply the checkout migration script in:

- `fastapi_backend/sql/migrations/20260819_checkout_stripe.sql`

## Facebook Login Notes

If you are enabling Facebook Login in Meta:

- App Domains:
  - `localhost`
- Site URL:
  - `http://localhost:3000`
- Valid OAuth Redirect URIs:
  - `https://<your-auth0-domain>/login/callback`

After that:

- Copy the Facebook App ID and App Secret into the Auth0 Facebook connection
- Enable the Facebook connection for your Auth0 app

## How to Run

### 1. Seed demo data

```powershell
cd fastapi_backend
python create_admin.py
```

### 2. Start FastAPI

```powershell
cd fastapi_backend
uvicorn app.main:app --reload
```

### 3. Start Django dashboard

```powershell
cd django_admin
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8080
```

### 4. Start frontend

```powershell
cd frontend
npm install
npm run dev
```

## How to Test

### FastAPI

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `GET /auth/auth0/me`
- `POST /auth/auth0/login`
- `GET /rbac/admin`
- `GET /rbac/staff`
- `GET /rbac/customer`
- `POST /cart/`
- `GET /cart/`
- `POST /checkout`
- `GET /orders/me`
- `GET /orders/{order_id}`
- `PATCH /orders/{order_id}/status` (admin/staff)
- `POST /payments/{order_id}/confirm`
- `GET /notifications` (supports `?page=`, `?page_size=`, `?read=`)
- `POST /notifications/read`
- WebSocket: `ws://127.0.0.1:8000/ws/notifications?token=<access_token>`

### Frontend

- Open the homepage
- Open `/products`
- Open `/cart`
- Open `/orders` for real-time order tracking, and `/orders/[id]` for a single order
- Test Auth0 login through the Login button
- Visit `/api/me` to confirm session data

### Django

- Open `/admin/` for built-in Django admin
- Open `/dashboard/` for analytics
- Open `/dashboard/orders/` for order management (mark orders shipped/delivered as staff — requires a Django superuser via `python manage.py createsuperuser`, and at least one `admin`/`staff` account in the FastAPI `users` table)

## Notification System

- Notifications are created for: order confirmed, payment success, payment failed, order shipped, order delivered.
- Delivered over three channels together: a DB row (`GET /notifications`), an email (via SMTP, see env vars below), and a live WebSocket push (`notification_created` / `order_status_updated` / `cart_updated` on `/ws/notifications`).
- Order status only moves forward (`pending → confirmed → paid → shipped → delivered`); invalid jumps are rejected with `400`.
- Both the Stripe webhook and the manual `POST /payments/{order_id}/confirm` endpoint go through the same notification flow, so a payment confirmed either way behaves identically.
- Apply `fastapi_backend/sql/migrations/20260824_notifications.sql` (or `alembic upgrade head`) on an existing database to add the `notifications` table.

## What Was Delivered

- FastAPI authentication implementation
- Database models for user, product, and cart
- Working JWT login flow
- Social login via Auth0
- Stripe checkout and payment flow
- Complete Postman collection and local environment under `postman/`
- Django analytics dashboard
- Frontend storefront pages

## Included Files

- `fastapi_backend/`
- `django_admin/`
- `frontend/`
- `postman/Smart-E-Commerce.postman_collection.json`
- `fastapi_backend/DEMO_CREDENTIALS.md`
- `fastapi_backend/.gitignore`
- `frontend/.gitignore`
