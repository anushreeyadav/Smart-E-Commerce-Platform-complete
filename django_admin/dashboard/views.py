from django.db import connection
from django.shortcuts import render


def table_exists(table_name):
    """
    Check whether a PostgreSQL table exists.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
            """,
            [table_name],
        )

        return cursor.fetchone()[0]


def column_exists(table_name, column_name):
    """
    Check whether a column exists in a PostgreSQL table.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                AND column_name = %s
            )
            """,
            [table_name, column_name],
        )

        return cursor.fetchone()[0]


def get_count(query, params=None):
    """
    Execute a COUNT query safely.
    """
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        result = cursor.fetchone()

        if result:
            return result[0] or 0

        return 0


def dashboard(request):
    """
    Main Django analytics dashboard.

    The dashboard reads analytics directly from the
    PostgreSQL database used by the FastAPI e-commerce backend.
    """

    # ---------------------------------------------------------
    # USERS
    # ---------------------------------------------------------

    total_users = 0
    customer_count = 0
    staff_count = 0
    admin_count = 0

    if table_exists("users"):

        total_users = get_count(
            """
            SELECT COUNT(*)
            FROM users
            """
        )

        # PostgreSQL enum-safe comparison.
        #
        # FastAPI may store enum labels as either uppercase names
        # (ADMIN/STAFF/CUSTOMER) or lowercase values depending on
        # how the type was created. LOWER(...) keeps this dashboard
        # compatible with both styles.
        customer_count = get_count(
            """
            SELECT COUNT(*)
            FROM users
            WHERE LOWER(role::text) = 'customer'
            """
        )

        staff_count = get_count(
            """
            SELECT COUNT(*)
            FROM users
            WHERE LOWER(role::text) = 'staff'
            """
        )

        admin_count = get_count(
            """
            SELECT COUNT(*)
            FROM users
            WHERE LOWER(role::text) = 'admin'
            """
        )


    # ---------------------------------------------------------
    # PRODUCTS
    # ---------------------------------------------------------

    total_products = 0
    products_in_stock = 0
    products_out_of_stock = 0

    if table_exists("products"):

        total_products = get_count(
            """
            SELECT COUNT(*)
            FROM products
            """
        )

        if column_exists("products", "stock"):

            products_in_stock = get_count(
                """
                SELECT COUNT(*)
                FROM products
                WHERE stock > 0
                """
            )

            products_out_of_stock = get_count(
                """
                SELECT COUNT(*)
                FROM products
                WHERE stock <= 0
                """
            )


    # ---------------------------------------------------------
    # CART
    # ---------------------------------------------------------

    total_cart_items = 0
    active_cart_items = 0

    if table_exists("cart_items"):

        total_cart_items = get_count(
            """
            SELECT COUNT(*)
            FROM cart_items
            """
        )

        active_cart_items = get_count(
            """
            SELECT COUNT(*)
            FROM cart_items
            WHERE quantity > 0
            """
        )


    # ---------------------------------------------------------
    # ORDERS
    # ---------------------------------------------------------

    total_orders = 0
    pending_orders = 0
    completed_orders = 0
    cancelled_orders = 0
    total_revenue = 0
    paid_payments = 0


    if table_exists("orders"):

        total_orders = get_count(
            """
            SELECT COUNT(*)
            FROM orders
            """
        )

        # -----------------------------------------------------
        # Order status analytics
        # -----------------------------------------------------

        if column_exists("orders", "status"):

            pending_orders = get_count(
                """
                SELECT COUNT(*)
                FROM orders
                WHERE LOWER(status::text) = 'pending'
                """
            )

            completed_orders = get_count(
                """
                SELECT COUNT(*)
                FROM orders
                WHERE LOWER(status::text) IN (
                    'confirmed',
                    'completed',
                    'delivered',
                    'paid'
                )
                """
            )

            cancelled_orders = get_count(
                """
                SELECT COUNT(*)
                FROM orders
                WHERE LOWER(status::text) IN (
                    'cancelled',
                    'canceled'
                )
                """
            )


        # -----------------------------------------------------
        # Payment / Revenue analytics
        # -----------------------------------------------------
        #
        # Revenue should follow the payment table because the
        # FastAPI flow marks payment as PAID and then confirms
        # the order. That gives us the most accurate money
        # number for the dashboard.
        #
        if table_exists("payments"):

            if column_exists("payments", "status"):

                paid_payments = get_count(
                    """
                    SELECT COUNT(*)
                    FROM payments
                    WHERE LOWER(status::text) = 'paid'
                    """
                )

            amount_column = None

            for column_name in [
                "amount",
                "total_amount",
                "grand_total",
                "payment_amount",
            ]:

                if column_exists("payments", column_name):
                    amount_column = column_name
                    break

            if amount_column:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT COALESCE(SUM({amount_column}), 0)
                        FROM payments
                        WHERE LOWER(status::text) = 'paid'
                        """
                    )

                    result = cursor.fetchone()

                    if result:
                        total_revenue = result[0] or 0

            elif column_exists("orders", "total_amount"):
                # Fallback if the payments table lacks an amount
                # column for some reason.
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(o.total_amount), 0)
                        FROM orders o
                        JOIN payments p ON p.order_id = o.id
                        WHERE LOWER(p.status::text) = 'paid'
                        """
                    )

                    result = cursor.fetchone()

                    if result:
                        total_revenue = result[0] or 0

        elif column_exists("orders", "total_amount"):
            # Last-resort fallback for older schemas.
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(total_amount), 0)
                    FROM orders
                    WHERE LOWER(status::text) IN (
                        'confirmed',
                        'completed',
                        'delivered',
                        'paid'
                    )
                    """
                )

                result = cursor.fetchone()

                if result:
                    total_revenue = result[0] or 0


    # ---------------------------------------------------------
    # DASHBOARD CONTEXT
    # ---------------------------------------------------------

    context = {
        # Users
        "total_users": total_users,
        "customer_count": customer_count,
        "staff_count": staff_count,
        "admin_count": admin_count,

        # Products
        "total_products": total_products,
        "products_in_stock": products_in_stock,
        "products_out_of_stock": products_out_of_stock,

        # Cart
        "total_cart_items": total_cart_items,
        "active_cart_items": active_cart_items,

        # Orders
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "paid_payments": paid_payments,

        # Revenue
        "total_revenue": total_revenue,
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context,
    )
