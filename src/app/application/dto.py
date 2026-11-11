from datetime import date

from pydantic import BaseModel, Field


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
