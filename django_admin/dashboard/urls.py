from django.urls import path

from . import orders_admin, report_views, views


app_name = "dashboard"


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("orders/", orders_admin.orders_list, name="orders"),
    path("reports/", report_views.reports_home, name="reports"),
    path("reports/orders/csv/", report_views.orders_csv, name="orders_csv"),
    path("reports/orders/pdf/", report_views.orders_pdf, name="orders_pdf"),
    path("reports/sales/csv/", report_views.sales_csv, name="sales_csv"),
    path("reports/sales/pdf/", report_views.sales_pdf, name="sales_pdf"),
    path("reports/users/csv/", report_views.users_csv, name="users_csv"),
    path("reports/users/pdf/", report_views.users_pdf, name="users_pdf"),
    path(
        "orders/<str:order_id>/status/",
        orders_admin.update_order_status,
        name="update_order_status",
    ),
]
