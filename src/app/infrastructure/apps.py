"""Django application configuration for infrastructure."""

from django.apps import AppConfig


class InfrastructureConfig(AppConfig):
    """Configure the booking infrastructure application."""

    name = "app.infrastructure"
    label = "booking"  # short, stable label for migrations / table ownership
    default_auto_field = "django.db.models.BigAutoField"
