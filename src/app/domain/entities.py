from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class Book(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    copies_total: int = Field(ge=0)
    copies_available: int = Field(ge=0)


class Reader(BaseModel):
    id: int
    full_name: str
    email: str


class Booking(BaseModel):
    id: int
    book_id: int
    reader_id: int
    start_date: date
    end_date: date
    status: BookingStatus = BookingStatus.ACTIVE
