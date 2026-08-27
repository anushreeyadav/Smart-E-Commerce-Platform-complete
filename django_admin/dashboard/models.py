from django.db import models


class User(models.Model):
    ROLE_ADMIN = "ADMIN"
    ROLE_STAFF = "STAFF"
    ROLE_CUSTOMER = "CUSTOMER"
    ROLE_CHOICES = (
        (ROLE_ADMIN, "admin"),
        (ROLE_STAFF, "staff"),
        (ROLE_CUSTOMER, "customer"),
    )

    id = models.CharField(max_length=36, primary_key=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    # This column is deliberately omitted from the admin form.  Django only
    # maps it so the model continues to match FastAPI's existing users table.
    password = models.CharField(max_length=255, null=True, blank=True)
    # SQLAlchemy's PostgreSQL Enum persists enum member names (ADMIN, STAFF,
    # CUSTOMER), while the labels keep the admin UI consistent with the API.
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "users"

    def __str__(self):
        return self.email


class Product(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    stock = models.IntegerField()
    images = models.JSONField(default=list)
    popularity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "products"

    def __str__(self):
        return self.name


class CartItem(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user_id = models.CharField(max_length=36)
    product_id = models.CharField(max_length=36)
    quantity = models.IntegerField()

    class Meta:
        managed = False
        db_table = "cart_items"

    def __str__(self):
        return f"{self.user_id} - {self.product_id}"


class Order(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"), ("CONFIRMED", "Confirmed"),
        ("PAID", "Paid"), ("SHIPPED", "Shipped"),
        ("DELIVERED", "Delivered"), ("CANCELLED", "Cancelled"),
    )
    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"), ("paid", "Paid"),
        ("failed", "Failed"), ("refunded", "Refunded"),
    )

    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, db_column="user_id", on_delete=models.DO_NOTHING)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    currency = models.CharField(max_length=3)
    stripe_checkout_session_id = models.CharField(max_length=120, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=120, null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "orders"

    def __str__(self):
        return self.id


class OrderItem(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    order = models.ForeignKey(Order, db_column="order_id", on_delete=models.DO_NOTHING)
    product = models.ForeignKey(Product, db_column="product_id", on_delete=models.DO_NOTHING)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = "order_items"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


class Payment(models.Model):
    STATUS_CHOICES = Order.PAYMENT_STATUS_CHOICES

    id = models.CharField(max_length=36, primary_key=True)
    order = models.OneToOneField(Order, db_column="order_id", on_delete=models.DO_NOTHING)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    provider = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    transaction_id = models.CharField(max_length=120, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "payments"
