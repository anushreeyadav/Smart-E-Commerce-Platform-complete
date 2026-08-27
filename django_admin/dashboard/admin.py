from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib import admin, messages
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from urllib.parse import urlparse

from .forms import OrderStatusAdminForm, ProductAdminForm
from .models import Order, OrderItem, Payment, Product, User


LOW_STOCK_THRESHOLD = 10


class StockStatusFilter(admin.SimpleListFilter):
    title = "stock status"
    parameter_name = "stock_status"

    def lookups(self, request, model_admin):
        return (
            ("in_stock", "In Stock"),
            ("low_stock", "Low Stock"),
            ("out_of_stock", "Out of Stock"),
        )

    def queryset(self, request, queryset):
        if self.value() == "in_stock":
            return queryset.filter(stock__gt=LOW_STOCK_THRESHOLD)
        if self.value() == "low_stock":
            return queryset.filter(stock__gt=0, stock__lte=LOW_STOCK_THRESHOLD)
        if self.value() == "out_of_stock":
            return queryset.filter(stock=0)
        return queryset


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product", "quantity", "unit_price", "subtotal")
    readonly_fields = fields

    @admin.display(description="Subtotal")
    def subtotal(self, obj):
        return obj.subtotal

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Historical order view; FastAPI remains the status-transition authority."""

    form = OrderStatusAdminForm
    list_display = ("id", "customer", "total_amount", "status_label", "payment_status_label", "created_at")
    list_filter = ("status", "payment_status", ("created_at", admin.DateFieldListFilter))
    search_fields = ("id", "user__name", "user__email", "payment__transaction_id")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25
    inlines = (OrderItemInline,)
    readonly_fields = (
        "id", "customer_name", "customer_email", "created_at", "total_amount", "currency",
        "payment_status_label", "payment_provider", "payment_transaction_id", "payment_amount",
        "payment_paid_at", "stripe_checkout_session_id", "stripe_payment_intent_id",
    )
    fields = (
        "id", "customer_name", "customer_email", "created_at", "total_amount", "currency", "status",
        "payment_status_label", "payment_provider", "payment_transaction_id", "payment_amount",
        "payment_paid_at", "stripe_checkout_session_id", "stripe_payment_intent_id",
    )

    @admin.display(description="Customer", ordering="user__email")
    def customer(self, obj):
        return obj.user.email

    @admin.display(description="Customer name")
    def customer_name(self, obj):
        return obj.user.name

    @admin.display(description="Customer email")
    def customer_email(self, obj):
        return obj.user.email

    @admin.display(description="Order status", ordering="status")
    def status_label(self, obj):
        return obj.get_status_display()

    @admin.display(description="Payment status", ordering="payment_status")
    def payment_status_label(self, obj):
        try:
            return obj.payment.get_status_display()
        except Payment.DoesNotExist:
            return obj.get_payment_status_display()

    @admin.display(description="Payment method")
    def payment_provider(self, obj):
        try:
            return obj.payment.provider
        except Payment.DoesNotExist:
            return obj.payment_method

    @admin.display(description="Transaction ID")
    def payment_transaction_id(self, obj):
        try:
            return obj.payment.transaction_id or "—"
        except Payment.DoesNotExist:
            return obj.stripe_payment_intent_id or "—"

    @admin.display(description="Payment amount")
    def payment_amount(self, obj):
        try:
            return obj.payment.amount
        except Payment.DoesNotExist:
            return "—"

    @admin.display(description="Payment date")
    def payment_paid_at(self, obj):
        try:
            return obj.payment.paid_at or "—"
        except Payment.DoesNotExist:
            return "—"

    def _can_view(self, request):
        return bool(request.user and request.user.is_active and (
            request.user.is_superuser or request.user.has_perm("dashboard.view_order")
        ))

    def _can_change(self, request):
        return bool(request.user and request.user.is_active and (
            request.user.is_superuser or request.user.has_perm("dashboard.change_order")
        ))

    def has_module_permission(self, request):
        return self._can_view(request) or self._can_change(request)

    def has_view_permission(self, request, obj=None):
        return self._can_view(request) or self._can_change(request)

    def has_change_permission(self, request, obj=None):
        return self._can_change(request)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        original = Order.objects.get(pk=obj.pk)
        if original.status == obj.status:
            return
        from .orders_admin import update_order_status_in_backend
        try:
            update_order_status_in_backend(obj.id, obj.status.lower())
        except Exception as exc:
            raise ValidationError(str(exc)) from exc
        obj.refresh_from_db()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = (
        "id",
        "name",
        "category",
        "price",
        "stock",
        "stock_status",
        "active_status",
        "created_at",
        "updated_at",
    )
    list_filter = ("category", StockStatusFilter, "is_active")
    search_fields = ("id", "name", "category")
    ordering = ("-updated_at",)
    date_hierarchy = "created_at"
    list_per_page = 25
    readonly_fields = ("id", "image_preview", "created_at", "updated_at")
    fields = (
        "id",
        "name",
        "description",
        "category",
        "price",
        "stock",
        "is_active",
        "image_preview",
        "image",
        "remove_image",
        "created_at",
        "updated_at",
    )
    actions = ("activate_selected", "deactivate_selected")

    @admin.display(description="Stock status", ordering="stock")
    def stock_status(self, obj):
        if obj.stock == 0:
            label, colour = "Out of Stock", "#b02a37"
        elif obj.stock <= LOW_STOCK_THRESHOLD:
            label, colour = "Low Stock", "#b36b00"
        else:
            label, colour = "In Stock", "#198754"
        return format_html('<span style="font-weight: 600; color: {}">{}</span>', colour, label)

    @admin.display(description="Active", ordering="is_active")
    def active_status(self, obj):
        label = "Active" if obj.is_active else "Inactive"
        colour = "#198754" if obj.is_active else "#b02a37"
        return format_html('<span style="font-weight: 600; color: {}">{}</span>', colour, label)

    @admin.display(description="Current image")
    def image_preview(self, obj):
        if not obj or not obj.images:
            return "No image"
        return format_html(
            '<img src="{}" alt="" style="max-height: 120px; max-width: 180px; object-fit: contain;" />',
            obj.images[0],
        )

    def _can_view(self, request):
        return bool(request.user and request.user.is_active and (
            request.user.is_superuser or request.user.has_perm("dashboard.view_product")
        ))

    def _can_change(self, request):
        return bool(request.user and request.user.is_active and (
            request.user.is_superuser or request.user.has_perm("dashboard.change_product")
        ))

    def has_module_permission(self, request):
        return self._can_view(request) or self._can_change(request)

    def has_view_permission(self, request, obj=None):
        return self._can_view(request) or self._can_change(request)

    def has_change_permission(self, request, obj=None):
        return self._can_change(request)

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        # Products are referenced by carts and historical order items.  Use the
        # reversible deactivate action instead of a destructive SQL delete.
        return False

    def save_model(self, request, obj, form, change):
        uploaded_image = form.cleaned_data.get("image")
        remove_image = form.cleaned_data.get("remove_image")
        images = list(obj.images or [])

        if remove_image and images:
            self._delete_local_image(images[0])
            images.pop(0)

        if uploaded_image:
            if images:
                self._delete_local_image(images[0])
                images.pop(0)
            filename = f"products/{uuid4().hex}{Path(uploaded_image.name).suffix.lower()}"
            stored_name = default_storage.save(filename, uploaded_image)
            image_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{stored_name}")
            images.insert(0, image_url)

        obj.images = images
        super().save_model(request, obj, form, change)

    @staticmethod
    def _delete_local_image(image_url):
        path = urlparse(image_url).path
        media_url = settings.MEDIA_URL.rstrip("/") + "/"
        if not path.startswith(media_url):
            return
        storage_name = path[len(media_url):]
        if default_storage.exists(storage_name):
            default_storage.delete(storage_name)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not (request.user and request.user.is_superuser):
            actions.pop("activate_selected", None)
            actions.pop("deactivate_selected", None)
        return actions

    @admin.action(description="Activate selected products")
    def activate_selected(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} product(s).", messages.SUCCESS)

    @admin.action(description="Deactivate selected products")
    def deactivate_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} product(s).", messages.SUCCESS)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Safe administration of the FastAPI-owned ``users`` table.

    The model is unmanaged: Django never creates, drops, or alters this table.
    Schema changes are owned by the FastAPI Alembic migrations.
    """

    list_display = (
        "id",
        "name",
        "email",
        "role_label",
        "account_status",
        "created_at",
    )
    list_filter = ("role", "is_active", ("created_at", admin.DateFieldListFilter))
    search_fields = ("id", "name", "email")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25
    readonly_fields = ("id", "created_at")
    fields = ("id", "name", "email", "role", "is_active", "created_at")
    actions = ("activate_selected", "deactivate_selected")

    @admin.display(description="Role", ordering="role")
    def role_label(self, obj):
        return obj.get_role_display()

    @admin.display(description="Status", ordering="is_active")
    def account_status(self, obj):
        label = "Active" if obj.is_active else "Inactive"
        colour = "#198754" if obj.is_active else "#b02a37"
        return format_html('<span style="font-weight: 600; color: {}">{}</span>', colour, label)

    def _is_admin(self, request):
        # The Django control-plane account is intentionally separate from
        # customer/API accounts.  Only Django superusers may manage roles or
        # account state, preventing a staff account from escalating privileges.
        return bool(request.user and request.user.is_active and request.user.is_superuser)

    def has_module_permission(self, request):
        return self._is_admin(request)

    def has_view_permission(self, request, obj=None):
        return self._is_admin(request)

    def has_change_permission(self, request, obj=None):
        return self._is_admin(request)

    def has_add_permission(self, request):
        # Customers must continue to be created through the existing FastAPI
        # registration/Auth0 paths, which handle passwords and identity safely.
        return False

    def has_delete_permission(self, request, obj=None):
        # Deactivation is recoverable and avoids deleting linked commerce data.
        return False

    @admin.action(description="Activate selected users")
    def activate_selected(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} user(s).", messages.SUCCESS)

    @admin.action(description="Deactivate selected users")
    def deactivate_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} user(s).", messages.SUCCESS)
