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
    def atomic(self) -> AbstractContextManager[None]:
        """Open a unit-of-work transaction."""
        ...


class BookRepository(ABC):
    """Define storage operations for books."""

    @abstractmethod
    def list(self) -> list[Book]:
        """List all records in the repository."""
        ...

    @abstractmethod
    def get(self, book_id: int) -> Book | None:
        """Get a record by its identifier."""
        ...

    @abstractmethod
    def get_by_isbn(self, isbn: str) -> Book | None:
        """Get a book by its ISBN."""
        ...

    @abstractmethod
    def get_for_update(self, book_id: int) -> Book | None:
        """Get and lock a book until the surrounding transaction ends.

        Call this inside ``UnitOfWork.atomic()`` to protect concurrent copy updates.
        """

    @abstractmethod
    def add(self, new_book: NewBook) -> Book:
        """Store and return the book.

        Raise BookAlreadyExistsError on a duplicate ISBN.
        """

    @abstractmethod
    def save(self, book: Book) -> Book:
        """Persist every field of an existing book.

        Raise BookNotFoundError if the book vanished, or BookAlreadyExistsError
        if the ISBN is duplicated.
        """

    @abstractmethod
    def delete(self, book_id: int) -> None:
        """Raise the relevant error if the book is missing or has bookings."""


class ReaderRepository(ABC):
    """Define storage operations for readers."""

    @abstractmethod
    def list(self) -> list[Reader]:
        """List all records in the repository."""
        ...

    @abstractmethod
    def get(self, reader_id: int) -> Reader | None:
        """Get a record by its identifier."""
        ...

    @abstractmethod
    def add(self, new_reader: NewReader) -> Reader:
        """Store and return the reader.

        Raise ReaderAlreadyExistsError on a duplicate email.
        """

    @abstractmethod
    def save(self, reader: Reader) -> Reader:
        """Raise an error if the reader is missing or the email is already used."""

    @abstractmethod
    def delete(self, reader_id: int) -> None:
        """Raise an error if the reader is missing or still has bookings."""


class BookingRepository(ABC):
    """Define storage operations for bookings."""

    @abstractmethod
    def list(self) -> list[Booking]:
        """List all records in the repository."""
        ...

    @abstractmethod
    def get(self, booking_id: int) -> Booking | None:
        """Get a record by its identifier."""
        ...

    @abstractmethod
    def get_for_update(self, booking_id: int) -> Booking | None:
        """Get and lock a booking inside ``UnitOfWork.atomic()``."""

    @abstractmethod
    def add(self, new_booking: NewBooking) -> Booking:
        """Add a new record to the repository."""
        ...

    @abstractmethod
    def save(self, booking: Booking) -> Booking:
        """Raise BookingNotFoundError if the booking no longer exists."""

    @abstractmethod
    def exists_for_book(self, book_id: int) -> bool:
        """Check whether a booking exists for the book."""
        ...

    @abstractmethod
    def exists_for_reader(self, reader_id: int) -> bool:
        """Check whether a booking exists for the reader."""
        ...
