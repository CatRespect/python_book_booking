"""Django ORM models = database tables. NOT the domain entities (see domain/entities.py)."""
from django.db import models
from django.db.models import F, Q

from app.domain.entities import BookingStatus


class BookModel(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=32, unique=True)
    copies_total = models.PositiveIntegerField()
    copies_available = models.PositiveIntegerField()

    class Meta:
        db_table = "books"
        constraints = [
            models.CheckConstraint(
                condition=Q(copies_available__lte=F("copies_total")),
                name="books_copies_available_lte_total",
            )
        ]


class ReaderModel(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    class Meta:
        db_table = "readers"


class BookingModel(models.Model):
    # PROTECT: deleting a book/reader that still has bookings is refused
    # (by Django, and ultimately by the foreign key in PostgreSQL).
    book = models.ForeignKey(BookModel, on_delete=models.PROTECT, related_name="bookings")
    reader = models.ForeignKey(ReaderModel, on_delete=models.PROTECT, related_name="bookings")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name.title()) for s in BookingStatus],
        default=BookingStatus.ACTIVE.value,
    )

    class Meta:
        db_table = "bookings"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="bookings_end_not_before_start",
            )
        ]
