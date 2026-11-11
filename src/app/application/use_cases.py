"""Use cases. STUBS: no logic yet, they return sample data.

Later: accept repositories (from app.domain.repositories) and implement the real flow.
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
from app.domain.entities import Book, Booking, Reader

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


def list_books() -> list[Book]:
    return [_SAMPLE_BOOK]


def get_book(book_id: int) -> Book:
    return _SAMPLE_BOOK.model_copy(update={"id": book_id})


def create_book(data: CreateBookInput) -> Book:
    return Book(id=1, copies_available=data.copies_total, **data.model_dump())


def list_readers() -> list[Reader]:
    return [_SAMPLE_READER]


def get_reader(reader_id: int) -> ReaderNameOutput:
    return ReaderNameOutput(full_name=_SAMPLE_READER.full_name)


def create_reader(data: CreateReaderInput) -> Reader:
    return Reader(id=1, **data.model_dump())


def update_reader(reader_id: int, data: UpdateReaderInput) -> Reader:
    changes = data.model_dump(exclude_unset=True)
    return _SAMPLE_READER.model_copy(update={"id": reader_id, **changes})


def remove_reader(reader_id: int) -> None:
    return None


def list_bookings() -> list[Booking]:
    return [_SAMPLE_BOOKING]


def get_booking(booking_id: int) -> BookingDetailsOutput:
    return BookingDetailsOutput(**_SAMPLE_BOOKING.model_dump(exclude={"id"}))


def create_booking(data: CreateBookingInput) -> Booking:
    return Booking(id=1, **data.model_dump())



def update_book(book_id: int, data: UpdateBookInput) -> Book:
    changes = data.model_dump(exclude_unset=True)
    return _SAMPLE_BOOK.model_copy(update={"id": book_id, **changes})


def remove_book(book_id: int) -> None:
    return None


def update_booking(booking_id: int, data: UpdateBookingInput) -> Booking:
    changes = data.model_dump(exclude_unset=True)
    return _SAMPLE_BOOKING.model_copy(update={"id": booking_id, **changes})


def remove_booking(booking_id: int) -> None:
    """Soft delete: later this should set status=CANCELLED instead of erasing the row."""
    return None
