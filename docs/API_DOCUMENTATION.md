# Smart E-Commerce API documentation

## Service URLs

- FastAPI: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Django Admin and analytics: `http://127.0.0.1:8001/admin/` and `/dashboard/`

## Authentication and roles

`POST /auth/login` returns an access and refresh token. Send FastAPI requests with `Authorization: Bearer <access_token>`. `/auth/refresh` accepts a refresh token; `/auth/me` returns the authenticated user. Auth0 users exchange an Auth0 bearer token at `POST /auth/auth0/login`.

Roles are enforced server-side: customers use cart/checkout and their own orders; staff/admin can operate products and orders; only admin can create or deactivate products. Deactivated accounts are rejected. Never add credentials, database URLs, Auth0 client secrets, Stripe keys, or webhook secrets to Postman exports.

## API groups

| Group | Routes | Access |
| --- | --- | --- |
| Products | `GET /products`, `GET /products/{id}`, `POST /products`, `PUT /products/{id}`, `DELETE /products/{id}` | Public reads; writes restricted by role. Delete performs soft deactivation. |
| Cart | `GET /cart`, `POST /cart/add`, `PUT /cart/update`, `DELETE /cart/remove` | Customer token. |
| Checkout | `POST /checkout` | Customer token; creates a Stripe checkout session. |
| Orders | `GET /orders/me`, `GET /orders/{id}`, `GET /orders`, `PATCH /orders/{id}/status` | Own orders for customer; list/status for staff/admin. |
| Payments | `GET /payments/me`, `GET /payments/{order_id}`, `GET /payments`, `POST /payments/{order_id}/confirm` | Own records for customer; list for staff/admin. |
| Notifications | `GET /notifications`, `POST /notifications/read` | Authenticated user. |
| RBAC | `GET /rbac/authenticated`, `/admin`, `/staff`, `/customer` | Matching role token. |
| Stripe webhook | `POST /webhooks/stripe` | Stripe signature required. |

Order statuses use the validated sequence `pending -> confirmed -> paid -> shipped -> delivered`, with permitted cancellation transitions. The webhook handles payment completion/failure idempotently.

## Django analytics and reports

These are server-rendered, session-authenticated Django routes; they do not accept FastAPI bearer tokens. A Django superuser is required:

- `GET /dashboard/?period=30d`
- `GET /dashboard/reports/`
- `/dashboard/reports/{orders,sales,users}/{csv,pdf}/`

Supported report/analytics periods are `today`, `yesterday`, `7d`, `30d`, `3m`, `12m`, or `custom` with ISO `start` and `end` values. Sales revenue includes only paid payments on non-cancelled orders.

## Errors and Stripe local testing

Typical FastAPI responses are `200`, `201`, `204`, `400` for invalid business requests, `401` for missing/invalid tokens, `403` for roles, `404` for absent resources, and `422` for invalid request schemas. Stripe webhook requests must carry a valid `Stripe-Signature`; use the Stripe CLI locally:

```powershell
stripe listen --forward-to http://127.0.0.1:8000/webhooks/stripe
```

Use Stripe test mode and test cards only. Do not call the webhook manually without a valid signature.
