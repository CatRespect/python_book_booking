"""Composition root: the ONLY place that knows both the ports and their Django implementations."""

from app.domain.repositories import (
    BookingRepository,
    BookRepository,
    ReaderRepository,
    UnitOfWork,
)
from app.infrastructure.repositories import (
    DjangoBookingRepository,
    DjangoBookRepository,
    DjangoReaderRepository,
    DjangoUnitOfWork,
)


def book_repository() -> BookRepository:
    return DjangoBookRepository()


def reader_repository() -> ReaderRepository:
    return DjangoReaderRepository()


def booking_repository() -> BookingRepository:
    return DjangoBookingRepository()


def unit_of_work() -> UnitOfWork:
    return DjangoUnitOfWork()
