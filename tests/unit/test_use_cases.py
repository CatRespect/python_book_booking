from datetime import date

import pytest

from app.application import use_cases
from app.application.dto import CreateBookingInput, CreateBookInput, CreateReaderInput
from app.domain.entities import BookingStatus
from app.domain.exceptions import (
    BookAlreadyExists,
    BookingNotFound,
    BookNotFound,
    InvalidBookingPeriod,
    ReaderAlreadyExists,
    ReaderNotFound,
)
from tests.unit.fakes import FakeBookingRepository, FakeBookRepository, FakeReaderRepository


@pytest.fixture
def repos():
    return FakeBookRepository(), FakeReaderRepository(), FakeBookingRepository()


def _book(isbn="111"):
    return CreateBookInput(title="T", author="A", isbn=isbn, copies_total=3)


def test_create_book_starts_with_all_copies_available(repos):
    books, _, _ = repos
    book = use_cases.create_book(books, _book())
    assert book.id == 1 and book.copies_available == 3


def test_duplicate_isbn_rejected(repos):
    books, _, _ = repos
    use_cases.create_book(books, _book())
    with pytest.raises(BookAlreadyExists):
        use_cases.create_book(books, _book())


def test_get_missing_entities_raise_not_found(repos):
    books, readers, bookings = repos
    with pytest.raises(BookNotFound):
        use_cases.get_book(books, 1)
    with pytest.raises(ReaderNotFound):
        use_cases.get_reader(readers, 1)
    with pytest.raises(BookingNotFound):
        use_cases.get_booking(bookings, 1)


def test_reader_roundtrip_and_duplicate_email(repos):
    _, readers, _ = repos
    data = CreateReaderInput(full_name="Jane", email="j@x.com")
    use_cases.create_reader(readers, data)
    assert use_cases.get_reader(readers, 1).full_name == "Jane"
    with pytest.raises(ReaderAlreadyExists):
        use_cases.create_reader(readers, data)


def _booking_input(**kw):
    base = dict(book_id=1, reader_id=1, start_date=date(2026, 1, 1), end_date=date(2026, 1, 5))
    return CreateBookingInput(**{**base, **kw})


def test_create_booking_happy_path(repos):
    books, readers, bookings = repos
    use_cases.create_book(books, _book())
    use_cases.create_reader(readers, CreateReaderInput(full_name="J", email="j@x.com"))
    booking = use_cases.create_booking(bookings, books, readers, _booking_input())
    assert booking.status == BookingStatus.ACTIVE
    assert use_cases.get_booking(bookings, booking.id).book_id == 1


def test_create_booking_rejects_bad_period(repos):
    books, readers, bookings = repos
    with pytest.raises(InvalidBookingPeriod):
        use_cases.create_booking(
            bookings, books, readers, _booking_input(end_date=date(2025, 12, 31))
        )


def test_create_booking_requires_existing_book_and_reader(repos):
    books, readers, bookings = repos
    with pytest.raises(BookNotFound):
        use_cases.create_booking(bookings, books, readers, _booking_input())
    use_cases.create_book(books, _book())
    with pytest.raises(ReaderNotFound):
        use_cases.create_booking(bookings, books, readers, _booking_input())
