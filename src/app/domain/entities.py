"""Python module for entities."""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.domain.exceptions import CopiesInUseError, NoCopiesAvailableError
from app.domain.validators import normalize_text


class BookingStatus(str, Enum):
    """Represent the lifecycle states of a booking."""

    ACTIVE = "active"
    RETURNED = "returned"
    CANCELLED = "cancelled"


# "New*" = data before it has been stored (no id yet).
# The stored entity extends it with the database-assigned id.
class NewBook(BaseModel):
    """Represent book data before it is stored."""

    title: str
    author: str
    isbn: str
    copies_total: int = Field(ge=0)
    copies_available: int = Field(ge=0)

    @model_validator(mode="after")
    def _available_not_above_total(self) -> "NewBook":
        """Ensure available copies do not exceed the total stock."""
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
        """Compare titles and authors, ignoring case and extra spaces."""
        return normalize_text(self.title) == normalize_text(title) and (
            normalize_text(self.author) == normalize_text(author)
        )

    def with_copy_taken(self) -> "Book":
        """Return a copy with one fewer available copy."""
        if self.copies_available < 1:
            raise NoCopiesAvailableError(self.id)
        return self.model_copy(update={"copies_available": self.copies_available - 1})

    def with_copy_returned(self) -> "Book":
        # min() keeps the invariant available <= total even if called twice by mistake.
        """Return a copy with one more available copy."""
        available = min(self.copies_available + 1, self.copies_total)
        return self.model_copy(update={"copies_available": available})

    def with_copies_added(self, count: int) -> "Book":
        """Return a copy with the requested copies added."""
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
            raise CopiesInUseError(self.id, on_loan)
        return self.model_copy(
            update={"copies_total": new_total, "copies_available": new_total - on_loan}
        )


class NewReader(BaseModel):
    """Represent reader data before it is stored."""

    full_name: str
    email: str


class Reader(NewReader):
    """Represent a stored reader."""

    id: int


class NewBooking(BaseModel):
    """Represent booking data before it is stored."""

    book_id: int
    reader_id: int
    start_date: date
    end_date: date
    status: BookingStatus = BookingStatus.ACTIVE


class Booking(NewBooking):
    """Represent a stored booking."""

    id: int
