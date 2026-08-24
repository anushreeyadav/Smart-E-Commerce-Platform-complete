from django.db import models


class User(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=20)
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
    stock = models.IntegerField()
    images = models.JSONField(default=list)
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