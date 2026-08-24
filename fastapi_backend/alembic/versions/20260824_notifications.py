"""add notifications table

Revision ID: 20260824_notifications
Revises: 20260819_checkout_stripe
Create Date: 2026-08-24

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260824_notifications"
down_revision: Union[str, Sequence[str], None] = "20260819_checkout_stripe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE notificationtype AS ENUM (
                'ORDER_CONFIRMED',
                'PAYMENT_SUCCESS',
                'PAYMENT_FAILED',
                'ORDER_SHIPPED',
                'ORDER_DELIVERED'
            );
        EXCEPTION
            WHEN duplicate_object THEN
                NULL;
        END $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            type notificationtype NOT NULL,
            message VARCHAR(500) NOT NULL,
            read_status BOOLEAN NOT NULL DEFAULT FALSE,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_id "
        "ON notifications (user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_read_status "
        "ON notifications (read_status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_timestamp "
        "ON notifications (timestamp);"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_timestamp "
        "ON notifications (user_id, timestamp DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_read_status "
        "ON notifications (user_id, read_status);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_read_status;")
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_timestamp;")
    op.execute("DROP INDEX IF EXISTS ix_notifications_timestamp;")
    op.execute("DROP INDEX IF EXISTS ix_notifications_read_status;")
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_id;")
    op.execute("DROP TABLE IF EXISTS notifications;")
    op.execute("DROP TYPE IF EXISTS notificationtype;")
