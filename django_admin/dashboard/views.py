from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.shortcuts import render
from django.utils import timezone


LOW_STOCK_THRESHOLD = 10
PERIODS = {
    "today": ("Today", 0), "yesterday": ("Yesterday", 1),
    "7d": ("Last 7 Days", 6), "30d": ("Last 30 Days", 29),
    "3m": ("Last 3 Months", 89), "12m": ("Last 12 Months", 364),
}


def _scalar(sql, params=()):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()[0] or 0


def _rows(sql, params=()):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _range(request):
    today = timezone.localdate()
    period = request.GET.get("period", "30d")
    if period == "custom":
        try:
            start = timezone.datetime.fromisoformat(request.GET["start"]).date()
            end = timezone.datetime.fromisoformat(request.GET["end"]).date()
            if end >= start:
                return period, "Custom Range", start, end
        except (KeyError, ValueError):
            pass
    label, days = PERIODS.get(period, PERIODS["30d"])
    end = today - timedelta(days=1) if period == "yesterday" else today
    return period, label, end - timedelta(days=days), end


def _series(rows, start, end, key):
    values = {str(row["day"]): float(row[key]) for row in rows}
    labels, data = [], []
    while start <= end:
        labels.append(start.strftime("%d %b"))
        data.append(values.get(start.isoformat(), 0))
        start += timedelta(days=1)
    return labels, data


@staff_member_required
def dashboard(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Analytics is restricted to administrators.")

    period, period_label, start, end = _range(request)
    dates = (start, end)
    valid_sale = "LOWER(p.status::text) = 'paid' AND LOWER(o.status::text) NOT IN ('cancelled', 'canceled')"

    total_users = _scalar("SELECT COUNT(*) FROM users")
    total_products = _scalar("SELECT COUNT(*) FROM products")
    total_orders = _scalar("SELECT COUNT(*) FROM orders")
    customers = _scalar("SELECT COUNT(*) FROM users WHERE LOWER(role::text) = 'customer'")
    staff = _scalar("SELECT COUNT(*) FROM users WHERE LOWER(role::text) = 'staff'")
    admins = _scalar("SELECT COUNT(*) FROM users WHERE LOWER(role::text) = 'admin'")
    pending_orders = _scalar("SELECT COUNT(*) FROM orders WHERE LOWER(status::text) = 'pending'")
    low_stock = _scalar("SELECT COUNT(*) FROM products WHERE stock > 0 AND stock <= %s AND is_active = TRUE", (LOW_STOCK_THRESHOLD,))
    out_of_stock = _scalar("SELECT COUNT(*) FROM products WHERE stock = 0 AND is_active = TRUE")
    low_stock_products = _rows("SELECT name, stock FROM products WHERE stock <= %s AND is_active = TRUE ORDER BY stock, name LIMIT 10", (LOW_STOCK_THRESHOLD,))

    revenue = _scalar(f"SELECT COALESCE(SUM(p.amount), 0) FROM payments p JOIN orders o ON o.id=p.order_id WHERE {valid_sale} AND COALESCE(p.paid_at,p.created_at)::date BETWEEN %s AND %s", dates)
    paid_orders = _scalar(f"SELECT COUNT(*) FROM payments p JOIN orders o ON o.id=p.order_id WHERE {valid_sale} AND COALESCE(p.paid_at,p.created_at)::date BETWEEN %s AND %s", dates)
    revenue_rows = _rows(f"SELECT COALESCE(p.paid_at,p.created_at)::date AS day, SUM(p.amount) AS amount FROM payments p JOIN orders o ON o.id=p.order_id WHERE {valid_sale} AND COALESCE(p.paid_at,p.created_at)::date BETWEEN %s AND %s GROUP BY day ORDER BY day", dates)
    sales_rows = _rows(f"SELECT COALESCE(p.paid_at,p.created_at)::date AS day, COUNT(*) AS count FROM payments p JOIN orders o ON o.id=p.order_id WHERE {valid_sale} AND COALESCE(p.paid_at,p.created_at)::date BETWEEN %s AND %s GROUP BY day ORDER BY day", dates)
    labels, revenue_data = _series(revenue_rows, start, end, "amount")
    _, sales_data = _series(sales_rows, start, end, "count")
    top_products = _rows(f"SELECT pr.name, SUM(oi.quantity) AS quantity FROM order_items oi JOIN products pr ON pr.id=oi.product_id JOIN orders o ON o.id=oi.order_id JOIN payments p ON p.order_id=o.id WHERE {valid_sale} AND COALESCE(p.paid_at,p.created_at)::date BETWEEN %s AND %s GROUP BY pr.id,pr.name ORDER BY quantity DESC LIMIT 8", dates)
    order_statuses = _rows("SELECT LOWER(status::text) AS label, COUNT(*) AS count FROM orders GROUP BY status ORDER BY label")
    payment_statuses = _rows("SELECT LOWER(status::text) AS label, COUNT(*) AS count FROM payments GROUP BY status ORDER BY label")

    return render(request, "dashboard/dashboard.html", {
        "period": period, "period_label": period_label, "start": start.isoformat(), "end": end.isoformat(),
        "total_users": total_users, "total_products": total_products, "total_orders": total_orders,
        "customers": customers, "staff": staff, "admins": admins, "pending_orders": pending_orders,
        "low_stock": low_stock, "out_of_stock": out_of_stock, "low_stock_products": low_stock_products,
        "revenue": revenue, "paid_orders": paid_orders, "average_order_value": revenue / paid_orders if paid_orders else 0,
        "trend_labels": labels, "revenue_data": revenue_data, "sales_data": sales_data,
        "top_products": top_products, "order_statuses": order_statuses, "payment_statuses": payment_statuses,
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
    })
