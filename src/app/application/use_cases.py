"""Use cases. STUBS: no logic yet, they return sample data.

Later: accept repositories (from app.domain.repositories) and implement the real flow.
"""
from datetime import date

from app.application.dto import CreateBookingInput, CreateBookInput, CreateReaderInput
from app.domain.entities import Book, Booking, BookingStatus, Reader

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


def create_reader(data: CreateReaderInput) -> Reader:
    return Reader(id=1, **data.model_dump())


def list_bookings() -> list[Booking]:
    return [_SAMPLE_BOOKING]


def create_booking(data: CreateBookingInput) -> Booking:
    return Booking(id=1, **data.model_dump())


def cancel_booking(booking_id: int) -> Booking:
    return _SAMPLE_BOOKING.model_copy(
        update={"id": booking_id, "status": BookingStatus.CANCELLED}
    )
