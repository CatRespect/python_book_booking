"""Data transfer objects for application use cases."""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.domain.entities import Book, BookingStatus

# Trimmed, non-empty, and no longer than the database columns (otherwise an over-long
# value would pass validation and then crash in PostgreSQL with a 500).
Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
Author = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
Isbn = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)
]
FullName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
# Email *format* is a business rule (domain/validators.py) checked in the use case.
Email = Annotated[str, StringConstraints(strip_whitespace=True, max_length=254)]


class CreateBookInput(BaseModel):
    """Register copies of a book.

    If a book with the same ISBN, title and author already exists, ``copies_total``
    is the number of copies ADDED to it (and to its available copies).
    """

    title: Title
    author: Author
    isbn: Isbn
    copies_total: int = Field(ge=1)


class CreateBookOutput(BaseModel):
    """Return the created book and whether it was newly registered."""

    book: Book
    created: bool  # False => the ISBN existed and copies were added to it


class CreateReaderInput(BaseModel):
    """Receive the name and email address of a new reader."""

    full_name: FullName
    email: Email


class CreateBookingInput(BaseModel):
    """Receive the book, reader, and dates for a new booking."""

    book_id: int
    reader_id: int
    start_date: date
    end_date: date


class UpdateBookInput(BaseModel):
    """All fields optional: PATCH only changes what the client sends.

    ``copies_total`` is the NEW total stock (not an increment). Copies currently on
    loan stay on loan, so ``copies_available`` is recomputed.
    """

    title: Title | None = None
    author: Author | None = None
    isbn: Isbn | None = None
    copies_total: int | None = Field(default=None, ge=1)


class UpdateReaderInput(BaseModel):
    """Receive the optional fields to update for a reader."""

    full_name: FullName | None = None
    email: Email | None = None


class UpdateBookingInput(BaseModel):
    """Receive the optional fields to update for a booking."""

    book_id: int | None = None
    reader_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None


class ReaderNameOutput(BaseModel):
    """Return the public name of a reader."""

    full_name: str


class BookingDetailsOutput(BaseModel):
    """Return the public details of a booking."""

    book_id: int
    reader_id: int
    start_date: date
    end_date: date
    status: BookingStatus
