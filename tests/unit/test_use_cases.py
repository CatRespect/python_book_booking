"""Unit tests for the application use cases."""

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
    BookHasBookingsError,
    BookingNotFoundError,
    BookNotFoundError,
    InvalidBookingPeriodError,
    InvalidEmailError,
    IsbnBelongsToAnotherBookError,
    NoCopiesAvailableError,
    ReaderAlreadyExistsError,
    ReaderHasBookingsError,
    ReaderNotFoundError,
)
from tests.unit.fakes import (
    FakeBookingRepository,
    FakeBookRepository,
    FakeReaderRepository,
    FakeUnitOfWork,
)

Repos = tuple[
    FakeBookRepository, FakeReaderRepository, FakeBookingRepository, FakeUnitOfWork
]
INITIAL_COPIES = 3
AVAILABLE_AFTER_UPDATE = 4


@pytest.fixture
def repos() -> Repos:
    """Build fake repositories for a use-case test."""
    books, readers, bookings = (
        FakeBookRepository(),
        FakeReaderRepository(),
        FakeBookingRepository(),
    )
    uow = FakeUnitOfWork(books, readers, bookings)
    return books, readers, bookings, uow


def _book(isbn: str = "111") -> CreateBookInput:
    """Build a book input for a use-case test."""
    return CreateBookInput(title="T", author="A", isbn=isbn, copies_total=3)


def test_create_book_starts_with_all_copies_available(repos: Repos) -> None:
    """Test create book starts with all copies available."""
    books, _, _, uow = repos
    book = use_cases.create_book(books, uow, _book()).book
    assert book.id == 1
    assert book.copies_available == INITIAL_COPIES


def test_duplicate_isbn_rejected(repos: Repos) -> None:
    """Test duplicate isbn rejected."""
    books, _, _, uow = repos
    use_cases.create_book(books, uow, _book())
    with pytest.raises(IsbnBelongsToAnotherBookError):
        use_cases.create_book(
            books,
            uow,
            CreateBookInput(title="X", author="A", isbn="111", copies_total=1),
        )


def test_get_missing_entities_raise_not_found(repos: Repos) -> None:
    """Test get missing entities raise not found."""
    books, readers, bookings, _uow = repos
    with pytest.raises(BookNotFoundError):
        use_cases.get_book(books, 1)
    with pytest.raises(ReaderNotFoundError):
        use_cases.get_reader(readers, 1)
    with pytest.raises(BookingNotFoundError):
        use_cases.get_booking(bookings, 1)


def test_reader_roundtrip_and_duplicate_email(repos: Repos) -> None:
    """Test reader roundtrip and duplicate email."""
    _, readers, _, _ = repos
    data = CreateReaderInput(full_name="Jane", email="j@x.com")
    use_cases.create_reader(readers, data)
    assert use_cases.get_reader(readers, 1).full_name == "Jane"
    with pytest.raises(ReaderAlreadyExistsError):
        use_cases.create_reader(readers, data)


def _booking_input(
    *,
    book_id: int = 1,
    reader_id: int = 1,
    start_date: date = date(2026, 1, 1),
    end_date: date = date(2026, 1, 5),
) -> CreateBookingInput:
    """Build booking input for a use-case test."""
    return CreateBookingInput(
        book_id=book_id,
        reader_id=reader_id,
        start_date=start_date,
        end_date=end_date,
    )


def test_create_booking_happy_path(repos: Repos) -> None:
    """Test create booking happy path."""
    books, readers, bookings, uow = repos
    use_cases.create_book(books, uow, _book())
    use_cases.create_reader(readers, CreateReaderInput(full_name="J", email="j@x.com"))
    booking = use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    assert booking.status == BookingStatus.ACTIVE
    assert use_cases.get_booking(bookings, booking.id).book_id == 1


def test_create_booking_rejects_bad_period(repos: Repos) -> None:
    """Test create booking rejects bad period."""
    books, readers, bookings, uow = repos
    with pytest.raises(InvalidBookingPeriodError):
        use_cases.create_booking(
            bookings, books, readers, uow, _booking_input(end_date=date(2025, 12, 31))
        )


def test_create_booking_requires_existing_book_and_reader(repos: Repos) -> None:
    """Test create booking requires existing book and reader."""
    books, readers, bookings, uow = repos
    with pytest.raises(BookNotFoundError):
        use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    use_cases.create_book(books, uow, _book())
    with pytest.raises(ReaderNotFoundError):
        use_cases.create_booking(bookings, books, readers, uow, _booking_input())


# ------------------------------------------------ availability / copies
def _setup(repos: Repos, total: int = 1) -> None:
    """Initialize repositories and a reader for a booking test."""
    books, readers, _bookings, uow = repos
    use_cases.create_book(
        books,
        uow,
        CreateBookInput(title="T", author="A", isbn="111", copies_total=total),
    )
    use_cases.create_reader(readers, CreateReaderInput(full_name="J", email="j@x.com"))


def test_booking_takes_a_copy_and_fails_at_zero(repos: Repos) -> None:
    """Test booking takes a copy and fails at zero."""
    books, readers, bookings, uow = repos
    _setup(repos, total=1)
    use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    book = books.get(1)
    assert book is not None
    assert book.copies_available == 0
    with pytest.raises(NoCopiesAvailableError):
        use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    assert len(bookings.items) == 1


def test_same_isbn_title_author_adds_copies(repos: Repos) -> None:
    """Test same isbn title author adds copies."""
    books, _, _, uow = repos
    first = use_cases.create_book(books, uow, _book())
    again = use_cases.create_book(
        books, uow, CreateBookInput(title=" t ", author="a", isbn="111", copies_total=2)
    )
    assert first.created
    assert not again.created
    assert (again.book.copies_total, again.book.copies_available) == (5, 5)


def test_same_isbn_other_title_is_conflict(repos: Repos) -> None:
    """Test same isbn other title is conflict."""
    books, _, _, uow = repos
    use_cases.create_book(books, uow, _book())
    with pytest.raises(IsbnBelongsToAnotherBookError):
        use_cases.create_book(
            books,
            uow,
            CreateBookInput(title="X", author="A", isbn="111", copies_total=1),
        )


def test_cancel_returns_copy_and_is_idempotent(repos: Repos) -> None:
    """Test cancel returns copy and is idempotent."""
    books, readers, bookings, uow = repos
    _setup(repos)
    use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    use_cases.remove_booking(bookings, books, uow, 1)
    use_cases.remove_booking(bookings, books, uow, 1)
    book = books.get(1)
    booking = bookings.get(1)
    assert book is not None
    assert booking is not None
    assert book.copies_available == 1
    assert booking.status == BookingStatus.CANCELLED


def test_move_booking_to_other_book_moves_the_copy(repos: Repos) -> None:
    """Test move booking to other book moves the copy."""
    books, readers, bookings, uow = repos
    _setup(repos)
    use_cases.create_book(
        books, uow, CreateBookInput(title="U", author="B", isbn="222", copies_total=1)
    )
    use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    use_cases.update_booking(
        bookings, books, readers, uow, 1, UpdateBookingInput(book_id=2)
    )
    first_book = books.get(1)
    second_book = books.get(2)
    assert first_book is not None
    assert second_book is not None
    assert (first_book.copies_available, second_book.copies_available) == (1, 0)


def test_update_and_delete_rules(repos: Repos) -> None:
    """Test update and delete rules."""
    books, readers, bookings, uow = repos
    _setup(repos, total=2)
    use_cases.create_booking(bookings, books, readers, uow, _booking_input())
    assert (
        use_cases.update_book(
            books, uow, 1, UpdateBookInput(copies_total=5)
        ).copies_available
        == AVAILABLE_AFTER_UPDATE
    )
    with pytest.raises(BookHasBookingsError):
        use_cases.remove_book(books, bookings, uow, 1)
    with pytest.raises(ReaderHasBookingsError):
        use_cases.remove_reader(readers, bookings, 1)
    with pytest.raises(InvalidEmailError):
        use_cases.update_reader(readers, 1, UpdateReaderInput(email="nope"))
    with pytest.raises(InvalidEmailError):
        use_cases.create_reader(readers, CreateReaderInput(full_name="X", email="a@b"))
