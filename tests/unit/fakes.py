"""In-memory repositories: let use cases be tested with NO database."""

import copy
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager

from app.domain.entities import Book, Booking, NewBook, NewBooking, NewReader, Reader
from app.domain.exceptions import (
    BookAlreadyExistsError,
    BookingNotFoundError,
    BookNotFoundError,
    ReaderAlreadyExistsError,
    ReaderNotFoundError,
)
from app.domain.repositories import (
    BookingRepository,
    BookRepository,
    ReaderRepository,
    UnitOfWork,
)


class FakeBookRepository(BookRepository):
    """Provide an in-memory book repository for tests."""

    def __init__(self) -> None:
        """Initialize the fake book repository."""
        self.items: dict[int, Book] = {}
        self._next_id = 1

    def list(self) -> list[Book]:
        """List all records in the repository."""
        return list(self.items.values())

    def get(self, book_id: int) -> Book | None:
        """Get a record by its identifier."""
        return self.items.get(book_id)

    def get_by_isbn(self, isbn: str) -> Book | None:
        """Get a book by its ISBN."""
        return next((b for b in self.items.values() if b.isbn == isbn), None)

    def get_for_update(self, book_id: int) -> Book | None:
        """Get a record and lock it for update."""
        return self.get(book_id)  # no concurrency in a single-threaded fake

    def add(self, new_book: NewBook) -> Book:
        """Add a new record to the repository."""
        if self.get_by_isbn(new_book.isbn):
            raise BookAlreadyExistsError(new_book.isbn)
        book = Book(id=self._next_id, **new_book.model_dump())
        self._next_id += 1
        self.items[book.id] = book
        return book

    def save(self, book: Book) -> Book:
        """Save an updated record in the repository."""
        if book.id not in self.items:
            raise BookNotFoundError(book.id)
        if any(b.isbn == book.isbn and b.id != book.id for b in self.items.values()):
            raise BookAlreadyExistsError(book.isbn)
        self.items[book.id] = book
        return book

    def delete(self, book_id: int) -> None:
        """Delete a record from the repository."""
        if self.items.pop(book_id, None) is None:
            raise BookNotFoundError(book_id)


class FakeReaderRepository(ReaderRepository):
    """Provide an in-memory reader repository for tests."""

    def __init__(self) -> None:
        """Initialize the fake reader repository."""
        self.items: dict[int, Reader] = {}
        self._next_id = 1

    def list(self) -> list[Reader]:
        """List all records in the repository."""
        return list(self.items.values())

    def get(self, reader_id: int) -> Reader | None:
        """Get a record by its identifier."""
        return self.items.get(reader_id)

    def add(self, new_reader: NewReader) -> Reader:
        """Add a new record to the repository."""
        if any(r.email == new_reader.email for r in self.items.values()):
            raise ReaderAlreadyExistsError(new_reader.email)
        reader = Reader(id=self._next_id, **new_reader.model_dump())
        self._next_id += 1
        self.items[reader.id] = reader
        return reader

    def save(self, reader: Reader) -> Reader:
        """Save an updated record in the repository."""
        if reader.id not in self.items:
            raise ReaderNotFoundError(reader.id)
        if any(
            r.email == reader.email and r.id != reader.id for r in self.items.values()
        ):
            raise ReaderAlreadyExistsError(reader.email)
        self.items[reader.id] = reader
        return reader

    def delete(self, reader_id: int) -> None:
        """Delete a record from the repository."""
        if self.items.pop(reader_id, None) is None:
            raise ReaderNotFoundError(reader_id)


class FakeBookingRepository(BookingRepository):
    """Provide an in-memory booking repository for tests."""

    def __init__(self) -> None:
        """Initialize the fake booking repository."""
        self.items: dict[int, Booking] = {}
        self._next_id = 1

    def list(self) -> list[Booking]:
        """List all records in the repository."""
        return list(self.items.values())

    def get(self, booking_id: int) -> Booking | None:
        """Get a record by its identifier."""
        return self.items.get(booking_id)

    def get_for_update(self, booking_id: int) -> Booking | None:
        """Get a record and lock it for update."""
        return self.get(booking_id)

    def add(self, new_booking: NewBooking) -> Booking:
        """Add a new record to the repository."""
        booking = Booking(id=self._next_id, **new_booking.model_dump())
        self._next_id += 1
        self.items[booking.id] = booking
        return booking

    def save(self, booking: Booking) -> Booking:
        """Save an updated record in the repository."""
        if booking.id not in self.items:
            raise BookingNotFoundError(booking.id)
        self.items[booking.id] = booking
        return booking

    def exists_for_book(self, book_id: int) -> bool:
        """Check whether a booking exists for the book."""
        return any(b.book_id == book_id for b in self.items.values())

    def exists_for_reader(self, reader_id: int) -> bool:
        """Check whether a booking exists for the reader."""
        return any(b.reader_id == reader_id for b in self.items.values())


class FakeUnitOfWork(UnitOfWork):
    """Behave like a real transaction and restore repositories after failures.

    This lets tests prove that nothing is written when a use case fails.
    """

    def __init__(
        self,
        *repos: FakeBookRepository | FakeReaderRepository | FakeBookingRepository,
    ) -> None:
        """Initialize the fake unit of work."""
        self._repos = repos

    def atomic(self) -> AbstractContextManager[None]:
        """Open a unit-of-work transaction."""
        return self._atomic()

    @contextmanager
    def _atomic(self) -> Iterator[None]:
        """Restore repository snapshots after transaction failures."""
        snapshots = [copy.deepcopy(r.items) for r in self._repos]
        try:
            yield
        except BaseException:
            for repo, snap in zip(self._repos, snapshots, strict=True):
                repo.items = snap
            raise
