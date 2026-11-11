"""Django ORM implementations of the domain repository ports."""

from contextlib import AbstractContextManager

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from app.domain.entities import Book, Booking, NewBook, NewBooking, NewReader, Reader
from app.domain.exceptions import (
    BookAlreadyExistsError,
    BookHasBookingsError,
    BookingNotFoundError,
    BookNotFoundError,
    ReaderAlreadyExistsError,
    ReaderHasBookingsError,
    ReaderNotFoundError,
)
from app.domain.repositories import (
    BookingRepository,
    BookRepository,
    ReaderRepository,
    UnitOfWork,
)
from app.infrastructure.models import BookingModel, BookModel, ReaderModel

_PG_UNIQUE_VIOLATION = "23505"


def _is_unique_violation(exc: IntegrityError) -> bool:
    """Return True only for a UNIQUE violation, not CHECK or FOREIGN KEY failures.

    Without this, any IntegrityError would be reported as "ISBN/email already exists",
    hiding the real problem.
    """
    return getattr(exc.__cause__, "sqlstate", None) == _PG_UNIQUE_VIOLATION


class DjangoUnitOfWork(UnitOfWork):
    """Provide Django transaction management."""

    def atomic(self) -> AbstractContextManager[None]:
        """Open a unit-of-work transaction."""
        return transaction.atomic()  # nested calls become savepoints


class DjangoBookRepository(BookRepository):
    """Implement book persistence with Django ORM queries."""

    def list(self) -> list[Book]:
        """List all records in the repository."""
        return [
            Book.model_validate(m, from_attributes=True)
            for m in BookModel.objects.order_by("id")
        ]

    def get(self, book_id: int) -> Book | None:
        """Get a record by its identifier."""
        model = BookModel.objects.filter(pk=book_id).first()
        return Book.model_validate(model, from_attributes=True) if model else None

    def get_by_isbn(self, isbn: str) -> Book | None:
        """Get a book by its ISBN."""
        model = BookModel.objects.filter(isbn=isbn).first()
        return Book.model_validate(model, from_attributes=True) if model else None

    def get_for_update(self, book_id: int) -> Book | None:
        # SELECT ... FOR UPDATE: other transactions wait here until we commit.
        """Get a record and lock it for update."""
        model = BookModel.objects.select_for_update().filter(pk=book_id).first()
        return Book.model_validate(model, from_attributes=True) if model else None

    def add(self, new_book: NewBook) -> Book:
        """Add a new record to the repository."""
        try:
            with (
                transaction.atomic()
            ):  # savepoint: keeps the connection usable after an error
                model = BookModel.objects.create(**new_book.model_dump())
        except IntegrityError as exc:
            if not _is_unique_violation(exc):
                raise
            raise BookAlreadyExistsError(new_book.isbn) from exc
        return Book.model_validate(model, from_attributes=True)

    def save(self, book: Book) -> Book:
        """Save an updated record in the repository."""
        try:
            with transaction.atomic():
                updated = BookModel.objects.filter(pk=book.id).update(
                    **book.model_dump(exclude={"id"})
                )
        except IntegrityError as exc:
            if not _is_unique_violation(exc):
                raise
            raise BookAlreadyExistsError(book.isbn) from exc
        if not updated:
            raise BookNotFoundError(book.id)
        return book

    def delete(self, book_id: int) -> None:
        """Delete a record from the repository."""
        try:
            deleted, _ = BookModel.objects.filter(pk=book_id).delete()
        except ProtectedError as exc:  # bookings still reference it (on_delete=PROTECT)
            raise BookHasBookingsError(book_id) from exc
        if not deleted:
            raise BookNotFoundError(book_id)


class DjangoReaderRepository(ReaderRepository):
    """Implement reader persistence with Django ORM queries."""

    def list(self) -> list[Reader]:
        """List all records in the repository."""
        return [
            Reader.model_validate(m, from_attributes=True)
            for m in ReaderModel.objects.order_by("id")
        ]

    def get(self, reader_id: int) -> Reader | None:
        """Get a record by its identifier."""
        model = ReaderModel.objects.filter(pk=reader_id).first()
        return Reader.model_validate(model, from_attributes=True) if model else None

    def add(self, new_reader: NewReader) -> Reader:
        """Add a new record to the repository."""
        try:
            with transaction.atomic():
                model = ReaderModel.objects.create(**new_reader.model_dump())
        except IntegrityError as exc:
            if not _is_unique_violation(exc):
                raise
            raise ReaderAlreadyExistsError(new_reader.email) from exc
        return Reader.model_validate(model, from_attributes=True)

    def save(self, reader: Reader) -> Reader:
        """Save an updated record in the repository."""
        try:
            with transaction.atomic():
                updated = ReaderModel.objects.filter(pk=reader.id).update(
                    **reader.model_dump(exclude={"id"})
                )
        except IntegrityError as exc:
            if not _is_unique_violation(exc):
                raise
            raise ReaderAlreadyExistsError(reader.email) from exc
        if not updated:
            raise ReaderNotFoundError(reader.id)
        return reader

    def delete(self, reader_id: int) -> None:
        """Delete a record from the repository."""
        try:
            deleted, _ = ReaderModel.objects.filter(pk=reader_id).delete()
        except ProtectedError as exc:
            raise ReaderHasBookingsError(reader_id) from exc
        if not deleted:
            raise ReaderNotFoundError(reader_id)


class DjangoBookingRepository(BookingRepository):
    """Implement booking persistence with Django ORM queries."""

    def list(self) -> list[Booking]:
        """List all records in the repository."""
        return [
            Booking.model_validate(m, from_attributes=True)
            for m in BookingModel.objects.order_by("id")
        ]

    def get(self, booking_id: int) -> Booking | None:
        """Get a record by its identifier."""
        model = BookingModel.objects.filter(pk=booking_id).first()
        return Booking.model_validate(model, from_attributes=True) if model else None

    def get_for_update(self, booking_id: int) -> Booking | None:
        """Get a record and lock it for update."""
        model = BookingModel.objects.select_for_update().filter(pk=booking_id).first()
        return Booking.model_validate(model, from_attributes=True) if model else None

    def add(self, new_booking: NewBooking) -> Booking:
        # book_id / reader_id existence is checked by the use case before this call;
        # the foreign keys remain the final safety net in the database.
        """Add a new record to the repository."""
        model = BookingModel.objects.create(**new_booking.model_dump(mode="python"))
        return Booking.model_validate(model, from_attributes=True)

    def save(self, booking: Booking) -> Booking:
        """Save an updated record in the repository."""
        fields = booking.model_dump(exclude={"id"})
        fields["status"] = booking.status.value  # store the plain string, not the Enum
        updated = BookingModel.objects.filter(pk=booking.id).update(**fields)
        if not updated:
            raise BookingNotFoundError(booking.id)
        return booking

    def exists_for_book(self, book_id: int) -> bool:
        """Check whether a booking exists for the book."""
        return BookingModel.objects.filter(book_id=book_id).exists()

    def exists_for_reader(self, reader_id: int) -> bool:
        """Check whether a booking exists for the reader."""
        return BookingModel.objects.filter(reader_id=reader_id).exists()
