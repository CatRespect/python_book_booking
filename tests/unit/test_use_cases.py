from datetime import date

import pytest

from app.application import use_cases
from app.application.dto import (
    CreateBookingInput,
    CreateBookInput,
    CreateReaderInput,
    UpdateBookingInput,
    UpdateBookInput,
    UpdateReaderInput,
)
from app.domain.entities import BookingStatus
from app.domain.exceptions import (
    BookHasBookings,
    BookingNotFound,
    BookNotFound,
    InvalidBookingPeriod,
    InvalidEmail,
    IsbnBelongsToAnotherBook,
    NoCopiesAvailable,
    ReaderAlreadyExists,
    ReaderHasBookings,
    ReaderNotFound,
)
from tests.unit.fakes import (
    FakeBookingRepository,
    FakeBookRepository,
    FakeReaderRepository,
    FakeUnitOfWork,
)


@pytest.fixture
def repos():
    books, readers, bookings = (
        FakeBookRepository(),
        FakeReaderRepository(),
        FakeBookingRepository(),
    )
    uow = FakeUnitOfWork(books, readers, bookings)
    return books, readers, bookings, uow


def _book(isbn="111"):
    return CreateBookInput(title="T", author="A", isbn=isbn, copies_total=3)


def test_create_book_starts_with_all_copies_available(repos):
    books, _, _, uow = repos
    book = use_cases.create_book(books, uow, _book()).book
    assert book.id == 1 and book.copies_available == 3


def test_duplicate_isbn_rejected(repos):
    books, _, _, uow = repos
    use_cases.create_book(books, uow, _book())
    with pytest.raises(IsbnBelongsToAnotherBook):
        use_cases.create_book(
            books,
            uow,
            CreateBookInput(title="X", author="A", isbn="111", copies_total=1),
        )


def test_get_missing_entities_raise_not_found(repos):
    books, readers, bookings, uow = repos
    with pytest.raises(BookNotFound):
        use_cases.get_book(books, 1)
    with pytest.raises(ReaderNotFound):
        use_cases.get_reader(readers, 1)
    with pytest.raises(BookingNotFound):
        use_cases.get_booking(bookings, 1)


def test_reader_roundtrip_and_duplicate_email(repos):
    _, readers, _, _ = repos
    data = CreateReaderInput(full_name="Jane", email="j@x.com")
    use_cases.create_reader(readers, data)
    assert use_cases.get_reader(readers, 1).full_name == "Jane"
    with pytest.raises(ReaderAlreadyExists):
        use_cases.create_reader(readers, data)


def _booking_input(**kw):
    base = dict(
        book_id=1, reader_id=1, start_date=date(2026, 1, 1), end_date=date(2026, 1, 5)
    )
    return CreateBookingInput(**{**base, **kw})


def test_create_booking_happy_path(repos):
    books, readers, bookings, uow = repos
    use_cases.create_book(books, uow, _book())
    use_cases.create_reader(readers, CreateReaderInput(full_name="J", email="j@x.com"))
    booking = use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    assert booking.status == BookingStatus.ACTIVE
    assert use_cases.get_booking(bookings, booking.id).book_id == 1


def test_create_booking_rejects_bad_period(repos):
    books, readers, bookings, uow = repos
    with pytest.raises(InvalidBookingPeriod):
        use_cases.create_booking(
            bookings, books, readers, uow, _booking_input(end_date=date(2025, 12, 31))
        )


def test_create_booking_requires_existing_book_and_reader(repos):
    books, readers, bookings, uow = repos
    with pytest.raises(BookNotFound):
        use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    use_cases.create_book(books, uow, _book())
    with pytest.raises(ReaderNotFound):
        use_cases.create_booking(bookings, books, readers, uow, _booking_input())


# ------------------------------------------------ availability / copies
def _setup(repos, total=1):
    books, readers, bookings, uow = repos
    use_cases.create_book(
        books,
        uow,
        CreateBookInput(title="T", author="A", isbn="111", copies_total=total),
    )
    use_cases.create_reader(readers, CreateReaderInput(full_name="J", email="j@x.com"))


def test_booking_takes_a_copy_and_fails_at_zero(repos):
    books, readers, bookings, uow = repos
    _setup(repos, total=1)
    use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    assert books.get(1).copies_available == 0
    with pytest.raises(NoCopiesAvailable):
        use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    assert len(bookings.items) == 1


def test_same_isbn_title_author_adds_copies(repos):
    books, _, _, uow = repos
    first = use_cases.create_book(books, uow, _book())
    again = use_cases.create_book(
        books, uow, CreateBookInput(title=" t ", author="a", isbn="111", copies_total=2)
    )
    assert first.created and not again.created
    assert (again.book.copies_total, again.book.copies_available) == (5, 5)


def test_same_isbn_other_title_is_conflict(repos):
    books, _, _, uow = repos
    use_cases.create_book(books, uow, _book())
    with pytest.raises(IsbnBelongsToAnotherBook):
        use_cases.create_book(
            books,
            uow,
            CreateBookInput(title="X", author="A", isbn="111", copies_total=1),
        )


def test_cancel_returns_copy_and_is_idempotent(repos):
    books, readers, bookings, uow = repos
    _setup(repos)
    use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    use_cases.remove_booking(bookings, books, uow, 1)
    use_cases.remove_booking(bookings, books, uow, 1)
    assert books.get(1).copies_available == 1
    assert bookings.get(1).status == BookingStatus.CANCELLED


def test_move_booking_to_other_book_moves_the_copy(repos):
    books, readers, bookings, uow = repos
    _setup(repos)
    use_cases.create_book(
        books, uow, CreateBookInput(title="U", author="B", isbn="222", copies_total=1)
    )
    use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    use_cases.update_booking(
        bookings, books, readers, uow, 1, UpdateBookingInput(book_id=2)
    )
    assert (books.get(1).copies_available, books.get(2).copies_available) == (1, 0)


def test_update_and_delete_rules(repos):
    books, readers, bookings, uow = repos
    _setup(repos, total=2)
    use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    assert (
        use_cases.update_book(
            books, uow, 1, UpdateBookInput(copies_total=5)
        ).copies_available
        == 4
    )
    with pytest.raises(BookHasBookings):
        use_cases.remove_book(books, bookings, uow, 1)
    with pytest.raises(ReaderHasBookings):
        use_cases.remove_reader(readers, bookings, 1)
    with pytest.raises(InvalidEmail):
        use_cases.update_reader(readers, 1, UpdateReaderInput(email="nope"))
    with pytest.raises(InvalidEmail):
        use_cases.create_reader(readers, CreateReaderInput(full_name="X", email="a@b"))
