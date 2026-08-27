from django.db import migrations, models


ORDER_STATUS_CHOICES = [
    ("PENDING", "Pending"), ("CONFIRMED", "Confirmed"),
    ("PAID", "Paid"), ("SHIPPED", "Shipped"),
    ("DELIVERED", "Delivered"), ("CANCELLED", "Cancelled"),
]
PAYMENT_STATUS_CHOICES = [
    ("pending", "Pending"), ("paid", "Paid"),
    ("failed", "Failed"), ("refunded", "Refunded"),
]


class Migration(migrations.Migration):
    """Django state for FastAPI-owned historical tables; no SQL is run."""

    dependencies = [("dashboard", "0003_product_management_state")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Order",
                    fields=[
                        ("id", models.CharField(max_length=36, primary_key=True, serialize=False)),
                        ("status", models.CharField(choices=ORDER_STATUS_CHOICES, max_length=20)),
                        ("payment_status", models.CharField(choices=PAYMENT_STATUS_CHOICES, max_length=20)),
                        ("total_amount", models.DecimalField(decimal_places=2, max_digits=10)),
                        ("payment_method", models.CharField(max_length=50)),
                        ("currency", models.CharField(max_length=3)),
                        ("stripe_checkout_session_id", models.CharField(blank=True, max_length=120, null=True)),
                        ("stripe_payment_intent_id", models.CharField(blank=True, max_length=120, null=True)),
                        ("created_at", models.DateTimeField()),
                        ("user", models.ForeignKey(db_column="user_id", on_delete=models.DO_NOTHING, to="dashboard.user")),
                    ],
                    options={"managed": False, "db_table": "orders"},
                ),
                migrations.CreateModel(
                    name="OrderItem",
                    fields=[
                        ("id", models.CharField(max_length=36, primary_key=True, serialize=False)),
                        ("quantity", models.IntegerField()),
                        ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                        ("order", models.ForeignKey(db_column="order_id", on_delete=models.DO_NOTHING, to="dashboard.order")),
                        ("product", models.ForeignKey(db_column="product_id", on_delete=models.DO_NOTHING, to="dashboard.product")),
                    ],
                    options={"managed": False, "db_table": "order_items"},
                ),
                migrations.CreateModel(
                    name="Payment",
                    fields=[
                        ("id", models.CharField(max_length=36, primary_key=True, serialize=False)),
                        ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                        ("provider", models.CharField(max_length=50)),
                        ("status", models.CharField(choices=PAYMENT_STATUS_CHOICES, max_length=20)),
                        ("transaction_id", models.CharField(blank=True, max_length=120, null=True)),
                        ("paid_at", models.DateTimeField(blank=True, null=True)),
                        ("created_at", models.DateTimeField()),
                        ("order", models.OneToOneField(db_column="order_id", on_delete=models.DO_NOTHING, to="dashboard.order")),
                    ],
                    options={"managed": False, "db_table": "payments"},
                ),
            ],
        )
    ]
