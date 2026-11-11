"""Use cases.

IMPLEMENTED (take repositories as the first arguments): list/get/create for books,
readers and bookings.
STUBS (bottom of file): update_* / remove_* still return sample data.
"""
from datetime import date

from app.application.dto import (
    BookingDetailsOutput,
    CreateBookingInput,
    CreateBookInput,
    CreateReaderInput,
    ReaderNameOutput,
    UpdateBookingInput,
    UpdateBookInput,
    UpdateReaderInput,
)
from app.domain.entities import (
    Book,
    Booking,
    NewBook,
    NewBooking,
    NewReader,
    Reader,
)
from app.domain.exceptions import (
    BookingNotFound,
    BookNotFound,
    InvalidBookingPeriod,
    ReaderNotFound,
)
from app.domain.repositories import BookingRepository, BookRepository, ReaderRepository


# ---------------------------------------------------------------- books
def list_books(books: BookRepository) -> list[Book]:
    return books.list()


def get_book(books: BookRepository, book_id: int) -> Book:
    book = books.get(book_id)
    if book is None:
        raise BookNotFound(book_id)
    return book


def create_book(books: BookRepository, data: CreateBookInput) -> Book:
    # A new title starts with every copy available.
    return books.add(NewBook(**data.model_dump(), copies_available=data.copies_total))


# -------------------------------------------------------------- readers
def list_readers(readers: ReaderRepository) -> list[Reader]:
    return readers.list()


def get_reader(readers: ReaderRepository, reader_id: int) -> ReaderNameOutput:
    reader = readers.get(reader_id)
    if reader is None:
        raise ReaderNotFound(reader_id)
    return ReaderNameOutput(full_name=reader.full_name)


def create_reader(readers: ReaderRepository, data: CreateReaderInput) -> Reader:
    return readers.add(NewReader(**data.model_dump()))


# ------------------------------------------------------------- bookings
def list_bookings(bookings: BookingRepository) -> list[Booking]:
    return bookings.list()


def get_booking(bookings: BookingRepository, booking_id: int) -> BookingDetailsOutput:
    booking = bookings.get(booking_id)
    if booking is None:
        raise BookingNotFound(booking_id)
    return BookingDetailsOutput(**booking.model_dump(exclude={"id"}))


def create_booking(
    bookings: BookingRepository,
    books: BookRepository,
    readers: ReaderRepository,
    data: CreateBookingInput,
) -> Booking:
    if data.end_date < data.start_date:
        raise InvalidBookingPeriod()
    if books.get(data.book_id) is None:
        raise BookNotFound(data.book_id)
    if readers.get(data.reader_id) is None:
        raise ReaderNotFound(data.reader_id)
    return bookings.add(NewBooking(**data.model_dump()))


# ======================================================== STUBS (no logic yet)
_SAMPLE_BOOK = Book(
    id=1,
    title="Clean Architecture",
    author="Robert C. Martin",
    isbn="9780134494166",
    copies_total=3,
    copies_available=3,
)
_SAMPLE_READER = Reader(id=1, full_name="Jane Doe", email="jane@example.com")
_SAMPLE_BOOKING = Booking(
    id=1,
    book_id=1,
    reader_id=1,
    start_date=date(2026, 1, 1),
    end_date=date(2026, 1, 14),
)


def update_book(book_id: int, data: UpdateBookInput) -> Book:
    changes = data.model_dump(exclude_unset=True)
    return _SAMPLE_BOOK.model_copy(update={"id": book_id, **changes})


def remove_book(book_id: int) -> None:
    return None


def update_reader(reader_id: int, data: UpdateReaderInput) -> Reader:
    changes = data.model_dump(exclude_unset=True)
    return _SAMPLE_READER.model_copy(update={"id": reader_id, **changes})


def remove_reader(reader_id: int) -> None:
    return None


def update_booking(booking_id: int, data: UpdateBookingInput) -> Booking:
    changes = data.model_dump(exclude_unset=True)
    return _SAMPLE_BOOKING.model_copy(update={"id": booking_id, **changes})


def remove_booking(booking_id: int) -> None:
    """Soft delete: later this should set status=CANCELLED instead of erasing the row."""
    return None
