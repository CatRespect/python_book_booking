import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]  # prototype only: restrict in production

INSTALLED_APPS = [
    "django.contrib.staticfiles",  # serves Swagger UI assets in dev
    "ninja",
    "app.infrastructure.apps.InfrastructureConfig",  # ORM models + migrations
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,  # needed for Swagger UI page
        "OPTIONS": {"context_processors": []},
    }
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Defaults match .env.example, so it works without loading the file.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "book_booking"),
        "USER": os.environ.get("POSTGRES_USER", "book_user"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "change_me"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,  # reuse connections instead of reconnecting per request
        "CONN_HEALTH_CHECKS": True,  # drop a stale reused connection instead of failing
    }
}

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
