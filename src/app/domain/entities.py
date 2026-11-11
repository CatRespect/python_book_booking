from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.domain.exceptions import CopiesInUse, NoCopiesAvailable
from app.domain.validators import normalize_text


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

    @model_validator(mode="after")
    def _available_not_above_total(self) -> "NewBook":
        if self.copies_available > self.copies_total:
            msg = "copies_available must not exceed copies_total"
            raise ValueError(msg)
        return self


class Book(NewBook):
    """A stored book. Copy-count rules live here, so every use case shares them.

    The methods never mutate: they return a changed copy (the caller then saves it).
    """

    id: int

    def is_same_edition(self, title: str, author: str) -> bool:
        """Same title and author (ignoring case and extra spaces)."""
        return normalize_text(self.title) == normalize_text(title) and (
            normalize_text(self.author) == normalize_text(author)
        )

    def with_copy_taken(self) -> "Book":
        if self.copies_available < 1:
            raise NoCopiesAvailable(self.id)
        return self.model_copy(update={"copies_available": self.copies_available - 1})

    def with_copy_returned(self) -> "Book":
        # min() keeps the invariant available <= total even if called twice by mistake.
        available = min(self.copies_available + 1, self.copies_total)
        return self.model_copy(update={"copies_available": available})

    def with_copies_added(self, count: int) -> "Book":
        return self.model_copy(
            update={
                "copies_total": self.copies_total + count,
                "copies_available": self.copies_available + count,
            }
        )

    def with_total_copies(self, new_total: int) -> "Book":
        """Change the stock; copies currently on loan stay on loan."""
        on_loan = self.copies_total - self.copies_available
        if new_total < on_loan:
            raise CopiesInUse(self.id, on_loan)
        return self.model_copy(
            update={"copies_total": new_total, "copies_available": new_total - on_loan}
        )


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
