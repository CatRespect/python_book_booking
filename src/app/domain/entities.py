from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    CANCELLED = "cancelled"


# "New*" = data before it has been stored (no id yet).
# The stored entity extends it with the database-assigned id.
class NewBook(BaseModel):
    title: str
    author: str
    isbn: str
    copies_total: int = Field(ge=0)
    copies_available: int = Field(ge=0)


class Book(NewBook):
    id: int


class NewReader(BaseModel):
    full_name: str
    email: str


class Reader(NewReader):
    id: int


class NewBooking(BaseModel):
    book_id: int
    reader_id: int
    start_date: date
    end_date: date
    status: BookingStatus = BookingStatus.ACTIVE


class Booking(NewBooking):
    id: int
