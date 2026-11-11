from datetime import date

from pydantic import BaseModel, Field

from app.domain.entities import BookingStatus


class CreateBookInput(BaseModel):
    title: str
    author: str
    isbn: str
    copies_total: int = Field(ge=1)


class CreateReaderInput(BaseModel):
    full_name: str
    email: str


class CreateBookingInput(BaseModel):
    book_id: int
    reader_id: int
    start_date: date
    end_date: date


class UpdateBookInput(BaseModel):
    """All fields optional: PATCH only changes what the client sends."""
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    copies_total: int | None = Field(default=None, ge=1)


class UpdateReaderInput(BaseModel):
    full_name: str | None = None
    email: str | None = None


class UpdateBookingInput(BaseModel):
    book_id: int | None = None
    reader_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None


class ReaderNameOutput(BaseModel):
    full_name: str


class BookingDetailsOutput(BaseModel):
    book_id: int
    reader_id: int
    start_date: date
    end_date: date
    status: BookingStatus
