import json
import time
import urllib.error
import urllib.request

import jwt
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.shortcuts import redirect, render


NEXT_STATUS_CHOICES = {
    "paid": ["shipped"],
    "shipped": ["delivered"],
}


def _mint_service_token() -> str | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, role
            FROM users
            WHERE LOWER(role::text) IN ('admin', 'staff')
            ORDER BY CASE WHEN LOWER(role::text) = 'admin' THEN 0 ELSE 1 END
            LIMIT 1
            """
        )
        row = cursor.fetchone()

    if not row:
        return None

    user_id, role = row

    payload = {
        "sub": user_id,
        "role": role.lower() if isinstance(role, str) else role,
        "type": "access",
        "exp": int(time.time()) + 120,
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _fetch_orders(limit: int = 200):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                o.id,
                LOWER(o.status::text),
                LOWER(o.payment_status),
                o.total_amount,
                o.currency,
                o.created_at,
                u.name,
                u.email
            FROM orders o
            JOIN users u ON u.id = o.user_id
            ORDER BY o.created_at DESC
            LIMIT %s
            """,
            [limit],
        )
        rows = cursor.fetchall()

    orders = []

    for row in rows:
        order_id, status, payment_status, total_amount, currency, created_at, name, email = row
        orders.append(
            {
                "id": order_id,
                "status": status,
                "payment_status": payment_status,
                "total_amount": total_amount,
                "currency": currency,
                "created_at": created_at,
                "customer_name": name,
                "customer_email": email,
                "next_statuses": NEXT_STATUS_CHOICES.get(status, []),
            }
        )

    return orders


@staff_member_required
def orders_list(request):
    orders = _fetch_orders()

    return render(
        request,
        "dashboard/orders.html",
        {"orders": orders},
    )


@staff_member_required
def update_order_status(request, order_id):
    if request.method != "POST":
        return redirect("dashboard:orders")

    new_status = request.POST.get("status", "").strip()

    if not new_status:
        messages.error(request, "No status selected.")
        return redirect("dashboard:orders")

    token = _mint_service_token()

    if not token:
        messages.error(
            request,
            "No admin/staff account exists in the FastAPI users table — "
            "run create_admin.py on the backend first.",
        )
        return redirect("dashboard:orders")

    api_request = urllib.request.Request(
        f"{settings.FASTAPI_BASE_URL}/orders/{order_id}/status",
        data=json.dumps({"status": new_status}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="PATCH",
    )

    try:
        with urllib.request.urlopen(api_request, timeout=10) as response:
            response.read()
        messages.success(request, f"Order {order_id} updated to '{new_status}'.")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        messages.error(request, f"Backend rejected the update: {detail}")
    except urllib.error.URLError as exc:
        messages.error(
            request,
            f"Could not reach the FastAPI backend at {settings.FASTAPI_BASE_URL}: {exc.reason}",
        )

    return redirect("dashboard:orders")
