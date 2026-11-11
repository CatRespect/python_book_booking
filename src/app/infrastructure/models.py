"""Django ORM models for database tables, separate from domain entities."""

from typing import ClassVar

from django.db import models
from django.db.models import F, Q

from app.domain.entities import BookingStatus


class BookModel(models.Model):
    """Represent a book row in the database."""

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=32, unique=True)
    copies_total = models.PositiveIntegerField()
    copies_available = models.PositiveIntegerField()

    def __str__(self) -> str:
        """Return the book title."""
        return self.title

    class Meta:
        """Define database metadata for the model."""

        db_table = "books"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(copies_available__lte=F("copies_total")),
                name="books_copies_available_lte_total",
            )
        ]


class ReaderModel(models.Model):
    """Represent a reader row in the database."""

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        """Return the reader's full name."""
        return self.full_name

    class Meta:
        """Define database metadata for the model."""

        db_table = "readers"


class BookingModel(models.Model):
    """Represent a booking row in the database."""

    # PROTECT: deleting a book/reader that still has bookings is refused
    # (by Django, and ultimately by the foreign key in PostgreSQL).

    book = models.ForeignKey(
        BookModel, on_delete=models.PROTECT, related_name="bookings"
    )
    reader = models.ForeignKey(
        ReaderModel, on_delete=models.PROTECT, related_name="bookings"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name.title()) for s in BookingStatus],
        default=BookingStatus.ACTIVE.value,
    )

    def __str__(self) -> str:
        """Return a readable booking identifier and status."""
        return f"Booking {self.pk} ({self.status})"

    class Meta:
        """Define database metadata for the model."""

        db_table = "bookings"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="bookings_end_not_before_start",
            )
        ]
