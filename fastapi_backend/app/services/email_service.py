import logging
import os
import smtplib
import time
from email.message import EmailMessage

from dotenv import load_dotenv
from fastapi import BackgroundTasks

from app.models.order import Order
from app.models.payment import Payment
from app.models.user import User


load_dotenv()

logger = logging.getLogger(__name__)


def send_email(
    *,
    recipient: str,
    subject: str,
    body: str,
) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM")

    if not all(
        [
            smtp_host,
            smtp_username,
            smtp_password,
            smtp_from,
        ]
    ):
        logger.warning(
            "Email '%s' to %s was not sent because SMTP settings are incomplete.",
            subject,
            recipient,
        )
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_from
    message["To"] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(message)

        return True
    except Exception:
        logger.exception("Unable to send email '%s' to %s.", subject, recipient)
        return False


MAX_EMAIL_ATTEMPTS = 3
RETRY_BASE_DELAY_SECONDS = 2.0


def send_email_with_retry(
    *,
    recipient: str,
    subject: str,
    body: str,
    max_attempts: int = MAX_EMAIL_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY_SECONDS,
) -> bool:
    for attempt in range(1, max_attempts + 1):
        if send_email(recipient=recipient, subject=subject, body=body):
            if attempt > 1:
                logger.info(
                    "Email '%s' to %s succeeded on attempt %s/%s.",
                    subject,
                    recipient,
                    attempt,
                    max_attempts,
                )
            return True

        if attempt < max_attempts:
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "Email '%s' to %s failed (attempt %s/%s). Retrying in %.0fs.",
                subject,
                recipient,
                attempt,
                max_attempts,
                delay,
            )
            time.sleep(delay)

    logger.error(
        "Email '%s' to %s permanently failed after %s attempts.",
        subject,
        recipient,
        max_attempts,
    )
    return False


def queue_email(
    background_tasks: BackgroundTasks,
    *,
    recipient: str,
    subject: str,
    body: str,
) -> None:
    background_tasks.add_task(
        send_email_with_retry,
        recipient=recipient,
        subject=subject,
        body=body,
    )


def queue_templated_email(
    background_tasks: BackgroundTasks,
    send_fn,
    *args,
    max_attempts: int = MAX_EMAIL_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY_SECONDS,
    **kwargs,
) -> None:
    def _run_with_retry() -> None:
        for attempt in range(1, max_attempts + 1):
            try:
                if send_fn(*args, **kwargs):
                    if attempt > 1:
                        logger.info(
                            "%s succeeded on attempt %s/%s.",
                            getattr(send_fn, "__name__", "email"),
                            attempt,
                            max_attempts,
                        )
                    return
            except Exception:
                logger.exception(
                    "%s raised on attempt %s/%s.",
                    getattr(send_fn, "__name__", "email"),
                    attempt,
                    max_attempts,
                )

            if attempt < max_attempts:
                time.sleep(base_delay * (2 ** (attempt - 1)))

        logger.error(
            "%s permanently failed after %s attempts.",
            getattr(send_fn, "__name__", "email"),
            max_attempts,
        )

    background_tasks.add_task(_run_with_retry)


_FOOTER = (
    "This is an automated message from Smart E-Commerce. "
    "Please do not reply to this email."
)


def render_email(
    *,
    greeting_name: str,
    headline: str,
    fields: list[tuple[str, str]],
    closing: str,
) -> str:
    lines = [f"Hello {greeting_name},", "", headline, ""]

    for label, value in fields:
        lines.append(f"{label}: {value}")

    lines.extend(["", closing, "", "-" * 40, _FOOTER])

    return "\n".join(lines)


def _format_money(order: Order) -> str:
    return f"{order.total_amount} {order.currency.upper()}"


def _format_timestamp(value) -> str:
    if value is None:
        return "N/A"
    return value.strftime("%Y-%m-%d %H:%M UTC")


def send_order_confirmation_email(
    user: User,
    order: Order,
) -> bool:
    body = render_email(
        greeting_name=user.name,
        headline=f"Your order {order.id} has been confirmed.",
        fields=[
            ("Order ID", order.id),
            ("Order status", order.status.value.replace("_", " ").title()),
            ("Order total", _format_money(order)),
            ("Placed at", _format_timestamp(order.created_at)),
        ],
        closing=(
            "We'll send another update as soon as your payment is "
            "processed and your order ships."
        ),
    )

    return send_email(
        recipient=user.email,
        subject=f"Order confirmed — {order.id}",
        body=body,
    )


def send_payment_success_email(
    user: User,
    order: Order,
    payment: Payment | None = None,
) -> bool:
    fields = [
        ("Order ID", order.id),
        ("Amount paid", _format_money(order)),
    ]

    if payment is not None and payment.paid_at is not None:
        fields.append(("Paid at", _format_timestamp(payment.paid_at)))

    body = render_email(
        greeting_name=user.name,
        headline=f"We received your payment for order {order.id}.",
        fields=fields,
        closing="Your order is now being processed.",
    )

    return send_email(
        recipient=user.email,
        subject=f"Payment successful — {order.id}",
        body=body,
    )


def send_payment_failed_email(
    user: User,
    order: Order,
) -> bool:
    body = render_email(
        greeting_name=user.name,
        headline=f"Your payment for order {order.id} was unsuccessful.",
        fields=[
            ("Order ID", order.id),
            ("Amount due", _format_money(order)),
        ],
        closing="Please try again or use another payment method.",
    )

    return send_email(
        recipient=user.email,
        subject=f"Payment failed — {order.id}",
        body=body,
    )


def send_order_shipped_email(
    user: User,
    order: Order,
    tracking_number: str | None = None,
) -> bool:
    fields = [
        ("Order ID", order.id),
        ("Order status", "Shipped"),
    ]

    if tracking_number:
        fields.append(("Tracking number", tracking_number))

    body = render_email(
        greeting_name=user.name,
        headline=f"Your order {order.id} has shipped.",
        fields=fields,
        closing=(
            "Tracking details will appear on your order page as soon as "
            "they're available."
            if not tracking_number
            else "You can use the tracking number above to follow your delivery."
        ),
    )

    return send_email(
        recipient=user.email,
        subject=f"Order shipped — {order.id}",
        body=body,
    )


def send_order_delivered_email(
    user: User,
    order: Order,
) -> bool:
    body = render_email(
        greeting_name=user.name,
        headline=f"Your order {order.id} has been delivered.",
        fields=[
            ("Order ID", order.id),
            ("Order status", "Delivered"),
        ],
        closing="We hope you enjoy your purchase. Thank you for shopping with us.",
    )

    return send_email(
        recipient=user.email,
        subject=f"Order delivered — {order.id}",
        body=body,
    )


send_shipping_update_email = send_order_shipped_email
