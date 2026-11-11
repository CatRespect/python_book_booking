"""Composition root for domain ports and their Django implementations."""

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
    """Create the Django book repository."""
    return DjangoBookRepository()


def reader_repository() -> ReaderRepository:
    """Create the Django reader repository."""
    return DjangoReaderRepository()


def booking_repository() -> BookingRepository:
    """Create the Django booking repository."""
    return DjangoBookingRepository()


def unit_of_work() -> UnitOfWork:
    """Create the Django unit of work."""
    return DjangoUnitOfWork()
