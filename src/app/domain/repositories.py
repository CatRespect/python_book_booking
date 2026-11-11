"""Ports: abstract storage interfaces. Implemented in infrastructure/repositories.py.

Update/delete methods will be added here when those operations get implemented.
"""
from abc import ABC, abstractmethod

from app.domain.entities import Book, Booking, NewBook, NewBooking, NewReader, Reader


class BookRepository(ABC):
    @abstractmethod
    def list(self) -> list[Book]: ...

    @abstractmethod
    def get(self, book_id: int) -> Book | None: ...

    @abstractmethod
    def add(self, new_book: NewBook) -> Book:
        """Store and return the book. Raises BookAlreadyExists on duplicate ISBN."""


class ReaderRepository(ABC):
    @abstractmethod
    def list(self) -> list[Reader]: ...

    @abstractmethod
    def get(self, reader_id: int) -> Reader | None: ...

    @abstractmethod
    def add(self, new_reader: NewReader) -> Reader:
        """Store and return the reader. Raises ReaderAlreadyExists on duplicate email."""


class BookingRepository(ABC):
    @abstractmethod
    def list(self) -> list[Booking]: ...

    @abstractmethod
    def get(self, booking_id: int) -> Booking | None: ...

    @abstractmethod
    def add(self, new_booking: NewBooking) -> Booking: ...
