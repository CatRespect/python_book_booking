"""URL configuration for the book booking API."""

from django.urls import path

from app.presentation.api import api

urlpatterns = [
    path("api/", api.urls),  # Swagger UI: /api/docs, schema: /api/openapi.json
]
