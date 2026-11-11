"""Django ORM models for database tables, separate from domain entities."""

from datetime import date
from typing import ClassVar

from django.db import models
from django.db.models import F, Q

from app.domain.entities import BookingStatus


class BookModel(models.Model):
    """Represent a book row in the database."""

    title: str = models.CharField(max_length=255)  # type: ignore[assignment]
    author: str = models.CharField(max_length=255)  # type: ignore[assignment]
    isbn: str = models.CharField(max_length=32, unique=True)  # type: ignore[assignment]
    copies_total: int = models.PositiveIntegerField()  # type: ignore[assignment]
    copies_available: int = models.PositiveIntegerField()  # type: ignore[assignment]

    class Meta:
        """Define database metadata for the model."""

        db_table = "books"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(copies_available__lte=F("copies_total")),
                name="books_copies_available_lte_total",
            )
        ]

    def __str__(self) -> str:
        """Return the book title."""
        return self.title


class ReaderModel(models.Model):
    """Represent a reader row in the database."""

    full_name: str = models.CharField(max_length=255)  # type: ignore[assignment]
    email: str = models.EmailField(unique=True)  # type: ignore[assignment]

    class Meta:
        """Define database metadata for the model."""

        db_table = "readers"

    def __str__(self) -> str:
        """Return the reader's full name."""
        return self.full_name


class BookingModel(models.Model):
    """Represent a booking row in the database."""

    # PROTECT: deleting a book/reader that still has bookings is refused
    # (by Django, and ultimately by the foreign key in PostgreSQL).

    book: BookModel = models.ForeignKey(  # type: ignore[assignment]
        BookModel, on_delete=models.PROTECT, related_name="bookings"
    )
    reader: ReaderModel = models.ForeignKey(  # type: ignore[assignment]
        ReaderModel, on_delete=models.PROTECT, related_name="bookings"
    )
    start_date: date = models.DateField()  # type: ignore[assignment]
    end_date: date = models.DateField()  # type: ignore[assignment]
    status: str = models.CharField(  # type: ignore[assignment]
        max_length=16,
        choices=[(s.value, s.name.title()) for s in BookingStatus],
        default=BookingStatus.ACTIVE.value,
    )

    class Meta:
        """Define database metadata for the model."""

        db_table = "bookings"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="bookings_end_not_before_start",
            )
        ]

    def __str__(self) -> str:
        """Return a readable booking identifier and status."""
        return f"Booking {self.pk} ({self.status})"
