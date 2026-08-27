#!/bin/sh
set -eu

# Create the base SQLAlchemy schema before applying the additive Alembic
# migrations. The migration history begins after the original tables existed.
python -c "from app.main import app"
alembic upgrade head
python create_admin.py

exec "$@"
