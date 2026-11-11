"""Django ORM implementations of the domain repository ports."""
from django.db import IntegrityError, transaction

from app.domain.entities import (
    Book,
    Booking,
    NewBook,
    NewBooking,
    NewReader,
    Reader,
)
from app.domain.exceptions import BookAlreadyExists, ReaderAlreadyExists
from app.domain.repositories import BookingRepository, BookRepository, ReaderRepository
from app.infrastructure.models import BookingModel, BookModel, ReaderModel


class DjangoBookRepository(BookRepository):
    def list(self) -> list[Book]:
        return [Book.model_validate(m, from_attributes=True) for m in BookModel.objects.order_by("id")]

    def get(self, book_id: int) -> Book | None:
        model = BookModel.objects.filter(pk=book_id).first()
        return Book.model_validate(model, from_attributes=True) if model else None

    def add(self, new_book: NewBook) -> Book:
        try:
            with transaction.atomic():  # savepoint: keeps the connection usable after an error
                model = BookModel.objects.create(**new_book.model_dump())
        except IntegrityError as exc:  # only the unique ISBN can fail for valid input
            raise BookAlreadyExists(new_book.isbn) from exc
        return Book.model_validate(model, from_attributes=True)


class DjangoReaderRepository(ReaderRepository):
    def list(self) -> list[Reader]:
        return [Reader.model_validate(m, from_attributes=True) for m in ReaderModel.objects.order_by("id")]

    def get(self, reader_id: int) -> Reader | None:
        model = ReaderModel.objects.filter(pk=reader_id).first()
        return Reader.model_validate(model, from_attributes=True) if model else None

    def add(self, new_reader: NewReader) -> Reader:
        try:
            with transaction.atomic():
                model = ReaderModel.objects.create(**new_reader.model_dump())
        except IntegrityError as exc:  # unique email
            raise ReaderAlreadyExists(new_reader.email) from exc
        return Reader.model_validate(model, from_attributes=True)


class DjangoBookingRepository(BookingRepository):
    def list(self) -> list[Booking]:
        return [Booking.model_validate(m, from_attributes=True) for m in BookingModel.objects.order_by("id")]

    def get(self, booking_id: int) -> Booking | None:
        model = BookingModel.objects.filter(pk=booking_id).first()
        return Booking.model_validate(model, from_attributes=True) if model else None

    def add(self, new_booking: NewBooking) -> Booking:
        # book_id / reader_id existence is checked by the use case before this call;
        # the foreign keys remain the final safety net in the database.
        model = BookingModel.objects.create(**new_booking.model_dump(mode="python"))
        return Booking.model_validate(model, from_attributes=True)
