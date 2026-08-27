from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .reports import csv_response, order_rows, pdf_response, report_range, sales_rows, user_rows


def _admin(view):
    @staff_member_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("Reports are restricted to administrators.")
        return view(request, *args, **kwargs)
    return wrapped


@_admin
def reports_home(request):
    start, end = report_range(request)
    return render(request, "dashboard/reports.html", {"start": start, "end": end, "period": request.GET.get("period", "30d")})


@_admin
def orders_csv(request):
    start, end = report_range(request)
    records = order_rows(start, end)
    rows = [[r["id"], r["name"], r["email"], r["created_at"].strftime("%Y-%m-%d %H:%M"), r["products"], r["total_amount"], r["order_status"], r["payment_status"], r["payment_method"], r["transaction_id"]] for r in records]
    return csv_response(f"orders_report_{start}_to_{end}.csv", ["Order ID","Customer","Email","Date","Products","Total","Order Status","Payment Status","Payment Method","Transaction ID"], rows)


@_admin
def orders_pdf(request):
    start, end = report_range(request)
    records = order_rows(start, end)
    rows = [[r["id"], r["name"], r["created_at"].strftime("%Y-%m-%d"), f"INR {r['total_amount']}", r["order_status"], r["payment_status"]] for r in records]
    return pdf_response(f"orders_report_{start}_to_{end}.pdf", "ORDERS REPORT", ["Order ID","Customer","Date","Total","Order","Payment"], rows, [f"Period: {start} to {end}", f"Total Orders: {len(rows)}"])


def _sales(request, as_pdf=False):
    start, end = report_range(request)
    records = sales_rows(start, end)
    total = sum((r["amount"] for r in records), 0)
    rows = [[r["sale_date"].strftime("%Y-%m-%d"), r["id"], r["name"], r["email"], r["amount"], r["payment_status"], r["provider"], r["transaction_id"]] for r in records]
    headers = ["Date","Order ID","Customer","Email","Amount","Payment Status","Method","Transaction ID"]
    if as_pdf:
        average = total / len(rows) if rows else 0
        return pdf_response(f"sales_report_{start}_to_{end}.pdf", "SALES REPORT", headers, rows, [f"Period: {start} to {end}", f"Total Revenue: INR {total:.2f}", f"Total Orders: {len(rows)}", f"Average Order Value: INR {average:.2f}"])
    return csv_response(f"sales_report_{start}_to_{end}.csv", headers, rows)


@_admin
def sales_csv(request): return _sales(request)


@_admin
def sales_pdf(request): return _sales(request, True)


def _users(request, as_pdf=False):
    start, end = report_range(request)
    records = user_rows(start, end)
    rows = [[r["id"], r["name"], r["email"], r["role"], "Active" if r["is_active"] else "Inactive", r["created_at"].strftime("%Y-%m-%d %H:%M")] for r in records]
    headers = ["User ID","Name","Email","Role","Status","Created Date"]
    if as_pdf:
        return pdf_response(f"users_report_{start}_to_{end}.pdf", "USER REPORT", headers, rows, [f"Period: {start} to {end}", f"Total Users: {len(rows)}"])
    return csv_response(f"users_report_{start}_to_{end}.csv", headers, rows)


@_admin
def users_csv(request): return _users(request)


@_admin
def users_pdf(request): return _users(request, True)
