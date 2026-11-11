"""Ports: abstract storage interfaces. Implemented later in infrastructure/."""
from abc import ABC, abstractmethod

from app.domain.entities import Book, Booking, Reader


class BookRepository(ABC):
    @abstractmethod
    def list(self) -> list[Book]: ...

    @abstractmethod
    def get(self, book_id: int) -> Book | None: ...

    @abstractmethod
    def add(self, book: Book) -> Book: ...


class ReaderRepository(ABC):
    @abstractmethod
    def list(self) -> list[Reader]: ...

    @abstractmethod
    def add(self, reader: Reader) -> Reader: ...


class BookingRepository(ABC):
    @abstractmethod
    def list(self) -> list[Booking]: ...

    @abstractmethod
    def get(self, booking_id: int) -> Booking | None: ...

    @abstractmethod
    def add(self, booking: Booking) -> Booking: ...
