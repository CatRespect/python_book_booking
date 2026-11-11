"""Composition root: the ONLY place that knows both the ports and their Django implementations."""
from app.domain.repositories import BookingRepository, BookRepository, ReaderRepository
from app.infrastructure.repositories import (
    DjangoBookingRepository,
    DjangoBookRepository,
    DjangoReaderRepository,
)


def book_repository() -> BookRepository:
    return DjangoBookRepository()


def reader_repository() -> ReaderRepository:
    return DjangoReaderRepository()


def booking_repository() -> BookingRepository:
    return DjangoBookingRepository()
