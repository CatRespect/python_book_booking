"""In-memory repositories: let use cases be tested with NO database."""

import copy
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager

from app.domain.entities import Book, Booking, NewBook, NewBooking, NewReader, Reader
from app.domain.exceptions import (
    BookAlreadyExists,
    BookingNotFound,
    BookNotFound,
    ReaderAlreadyExists,
    ReaderNotFound,
)
from app.domain.repositories import (
    BookingRepository,
    BookRepository,
    ReaderRepository,
    UnitOfWork,
)


class FakeBookRepository(BookRepository):
    def __init__(self):
        self.items: dict[int, Book] = {}
        self._next_id = 1

    def list(self):
        return list(self.items.values())

    def get(self, book_id):
        return self.items.get(book_id)

    def get_by_isbn(self, isbn):
        return next((b for b in self.items.values() if b.isbn == isbn), None)

    def get_for_update(self, book_id):
        return self.get(book_id)  # no concurrency in a single-threaded fake

    def add(self, new_book: NewBook):
        if self.get_by_isbn(new_book.isbn):
            raise BookAlreadyExists(new_book.isbn)
        book = Book(id=self._next_id, **new_book.model_dump())
        self._next_id += 1
        self.items[book.id] = book
        return book

    def save(self, book: Book):
        if book.id not in self.items:
            raise BookNotFound(book.id)
        if any(b.isbn == book.isbn and b.id != book.id for b in self.items.values()):
            raise BookAlreadyExists(book.isbn)
        self.items[book.id] = book
        return book

    def delete(self, book_id):
        if self.items.pop(book_id, None) is None:
            raise BookNotFound(book_id)


class FakeReaderRepository(ReaderRepository):
    def __init__(self):
        self.items: dict[int, Reader] = {}
        self._next_id = 1

    def list(self):
        return list(self.items.values())

    def get(self, reader_id):
        return self.items.get(reader_id)

    def add(self, new_reader: NewReader):
        if any(r.email == new_reader.email for r in self.items.values()):
            raise ReaderAlreadyExists(new_reader.email)
        reader = Reader(id=self._next_id, **new_reader.model_dump())
        self._next_id += 1
        self.items[reader.id] = reader
        return reader

    def save(self, reader: Reader):
        if reader.id not in self.items:
            raise ReaderNotFound(reader.id)
        if any(
            r.email == reader.email and r.id != reader.id for r in self.items.values()
        ):
            raise ReaderAlreadyExists(reader.email)
        self.items[reader.id] = reader
        return reader

    def delete(self, reader_id):
        if self.items.pop(reader_id, None) is None:
            raise ReaderNotFound(reader_id)


class FakeBookingRepository(BookingRepository):
    def __init__(self):
        self.items: dict[int, Booking] = {}
        self._next_id = 1

    def list(self):
        return list(self.items.values())

    def get(self, booking_id):
        return self.items.get(booking_id)

    def get_for_update(self, booking_id):
        return self.get(booking_id)

    def add(self, new_booking: NewBooking):
        booking = Booking(id=self._next_id, **new_booking.model_dump())
        self._next_id += 1
        self.items[booking.id] = booking
        return booking

    def save(self, booking: Booking):
        if booking.id not in self.items:
            raise BookingNotFound(booking.id)
        self.items[booking.id] = booking
        return booking

    def exists_for_book(self, book_id):
        return any(b.book_id == book_id for b in self.items.values())

    def exists_for_reader(self, reader_id):
        return any(b.reader_id == reader_id for b in self.items.values())


class FakeUnitOfWork(UnitOfWork):
    """Behaves like a real transaction: if the block raises, every repository is rolled
    back to its state at entry. This lets tests prove "nothing is written on failure".
    """

    def __init__(self, *repos):
        self._repos = repos

    def atomic(self) -> AbstractContextManager[None]:
        return self._atomic()

    @contextmanager
    def _atomic(self) -> Iterator[None]:
        snapshots = [copy.deepcopy(r.items) for r in self._repos]
        try:
            yield
        except BaseException:
            for repo, snap in zip(self._repos, snapshots, strict=True):
                repo.items = snap
            raise
