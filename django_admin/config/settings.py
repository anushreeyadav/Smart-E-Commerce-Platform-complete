from pathlib import Path
import os
from urllib.parse import urlparse


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# LOAD .ENV FILE
# ============================================================

# Your .env is currently inside fastapi_backend.
# Django project is next to fastapi_backend, so we check both
# locations.

ENV_FILES = [
    BASE_DIR / ".env",
    BASE_DIR.parent / "fastapi_backend" / ".env",
]

for env_file in ENV_FILES:
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)

                key = key.strip()
                value = value.strip()

                # Remove surrounding quotes if present
                if (
                    len(value) >= 2
                    and value[0] == value[-1]
                    and value[0] in ('"', "'")
                ):
                    value = value[1:-1]

                os.environ.setdefault(key, value)


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-development-secret-key-change-this-in-production",
)

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    # Django built-in applications
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "dashboard",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = "config.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# WSGI
# ============================================================

WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# DATABASE
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/Ekart",
)


def parse_database_url(database_url):
    """
    Convert PostgreSQL DATABASE_URL into Django DATABASES format.
    """

    parsed = urlparse(database_url)

    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError(
            "DATABASE_URL must use postgresql:// or postgres://"
        )

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
    }


DATABASES = {
    "default": parse_database_url(DATABASE_URL)
}


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]


# ============================================================
# MEDIA FILES
# ============================================================

MEDIA_URL = "media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# DJANGO ADMIN
# ============================================================

LOGIN_URL = "/admin/login/"

LOGIN_REDIRECT_URL = "/admin/"

LOGOUT_REDIRECT_URL = "/admin/login/"


# ============================================================
# AUTH0 CONFIGURATION
# ============================================================

AUTH0_DOMAIN = os.getenv(
    "AUTH0_DOMAIN",
    "your-tenant.us.auth0.com",
)

AUTH0_CLIENT_ID = os.getenv(
    "AUTH0_CLIENT_ID",
    "your-client-id",
)

AUTH0_CLIENT_SECRET = os.getenv(
    "AUTH0_CLIENT_SECRET",
    "your-client-secret",
)

AUTH0_AUDIENCE = os.getenv(
    "AUTH0_AUDIENCE",
    "https://smart-ecommerce-api",
)


# ============================================================
# FASTAPI BACKEND
# ============================================================

FASTAPI_BASE_URL = os.getenv(
    "FASTAPI_BASE_URL",
    "http://127.0.0.1:8000",
)


# ============================================================
# JWT CONFIGURATION
# ============================================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change-this-to-a-long-random-secret-key",
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "30",
    )
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv(
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "7",
    )
)


# ============================================================
# SECURITY SETTINGS FOR LOCAL DEVELOPMENT
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

SECURE_SSL_REDIRECT = False

SESSION_COOKIE_SECURE = False

CSRF_COOKIE_SECURE = False


# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": (
                "{levelname} {asctime} {module} "
                "{process:d} {thread:d} {message}"
            ),
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },

    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}