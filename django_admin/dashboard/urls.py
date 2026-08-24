from django.urls import path

from . import orders_admin, views


app_name = "dashboard"


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("orders/", orders_admin.orders_list, name="orders"),
    path(
        "orders/<str:order_id>/status/",
        orders_admin.update_order_status,
        name="update_order_status",
    ),
]