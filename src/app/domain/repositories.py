"""Ports: abstract storage interfaces. Implemented in infrastructure/repositories.py."""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager

from app.domain.entities import Book, Booking, NewBook, NewBooking, NewReader, Reader


class UnitOfWork(ABC):
    """A transaction boundary, expressed without naming any database.

    Use cases that change several rows (book copies + booking) wrap them in
    ``with uow.atomic():`` so either everything is stored or nothing is.
    """

    @abstractmethod
    def atomic(self) -> AbstractContextManager[None]: ...


class BookRepository(ABC):
    @abstractmethod
    def list(self) -> list[Book]: ...

    @abstractmethod
    def get(self, book_id: int) -> Book | None: ...

    @abstractmethod
    def get_by_isbn(self, isbn: str) -> Book | None: ...

    @abstractmethod
    def get_for_update(self, book_id: int) -> Book | None:
        """Like get(), but locks the row until the surrounding transaction ends.

        Must be called inside ``UnitOfWork.atomic()``. This is what makes
        "read copies_available, then change it" safe under concurrent requests.
        """

    @abstractmethod
    def add(self, new_book: NewBook) -> Book:
        """Store and return the book. Raises BookAlreadyExists on duplicate ISBN."""

    @abstractmethod
    def save(self, book: Book) -> Book:
        """Persist every field of an existing book.

        Raises BookNotFound if it vanished, BookAlreadyExists on duplicate ISBN.
        """

    @abstractmethod
    def delete(self, book_id: int) -> None:
        """Raises BookNotFound, or BookHasBookings if bookings still reference it."""


class ReaderRepository(ABC):
    @abstractmethod
    def list(self) -> list[Reader]: ...

    @abstractmethod
    def get(self, reader_id: int) -> Reader | None: ...

    @abstractmethod
    def add(self, new_reader: NewReader) -> Reader:
        """Store and return the reader. Raises ReaderAlreadyExists on duplicate email."""

    @abstractmethod
    def save(self, reader: Reader) -> Reader:
        """Raises ReaderNotFound, or ReaderAlreadyExists on duplicate email."""

    @abstractmethod
    def delete(self, reader_id: int) -> None:
        """Raises ReaderNotFound, or ReaderHasBookings if bookings still reference it."""


class BookingRepository(ABC):
    @abstractmethod
    def list(self) -> list[Booking]: ...

    @abstractmethod
    def get(self, booking_id: int) -> Booking | None: ...

    @abstractmethod
    def get_for_update(self, booking_id: int) -> Booking | None:
        """get() + row lock; call inside ``UnitOfWork.atomic()``."""

    @abstractmethod
    def add(self, new_booking: NewBooking) -> Booking: ...

    @abstractmethod
    def save(self, booking: Booking) -> Booking:
        """Raises BookingNotFound if the booking vanished."""

    @abstractmethod
    def exists_for_book(self, book_id: int) -> bool: ...

    @abstractmethod
    def exists_for_reader(self, reader_id: int) -> bool: ...
