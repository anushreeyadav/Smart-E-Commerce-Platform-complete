from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from .models import Order, Product


MAX_PRODUCT_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_PRODUCT_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


class ProductAdminForm(forms.ModelForm):
    """Adds a validated primary-image upload to the shared Product model."""

    image = forms.ImageField(required=False, help_text="JPEG, PNG, or WEBP; maximum 5 MB.")
    remove_image = forms.BooleanField(
        required=False,
        help_text="Remove the current primary image without changing other image URLs.",
    )

    class Meta:
        model = Product
        fields = ("name", "description", "category", "price", "stock", "is_active")

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image

        if image.size > MAX_PRODUCT_IMAGE_SIZE:
            raise ValidationError("Image must be 5 MB or smaller.")

        image_format = getattr(image, "image", None)
        image_format = getattr(image_format, "format", "").upper()
        if image_format not in ALLOWED_PRODUCT_IMAGE_FORMATS:
            allowed = ", ".join(sorted(ALLOWED_PRODUCT_IMAGE_FORMATS))
            raise ValidationError(f"Unsupported image format. Use {allowed}.")

        suffix = Path(image.name).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise ValidationError("Image filename must end in .jpg, .jpeg, .png, or .webp.")

        return image

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise ValidationError("Product name must contain at least 2 characters.")
        return name

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price <= 0:
            raise ValidationError("Price must be greater than zero.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data["stock"]
        if stock < 0:
            raise ValidationError("Stock cannot be negative.")
        return stock


ORDER_STATUS_TRANSITIONS = {
    "PENDING": ("CONFIRMED", "CANCELLED"),
    "CONFIRMED": ("PAID", "CANCELLED"),
    "PAID": ("SHIPPED", "CANCELLED"),
    "SHIPPED": ("DELIVERED",),
    "DELIVERED": (),
    "CANCELLED": (),
}


class OrderStatusAdminForm(forms.ModelForm):
    """Show only FastAPI-compatible transitions in the Django admin."""

    class Meta:
        model = Order
        fields = ("status",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            return

        current = self.instance.status
        allowed = ORDER_STATUS_TRANSITIONS.get(current, ())
        labels = dict(Order.STATUS_CHOICES)
        self.fields["status"].choices = [(current, labels[current])] + [
            (value, labels[value]) for value in allowed
        ]
        if not allowed:
            self.fields["status"].disabled = True
