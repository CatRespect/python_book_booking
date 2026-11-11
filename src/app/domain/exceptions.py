"""Domain errors. Pure Python: they know nothing about HTTP.

The presentation layer maps each *category* to a status code
(NotFoundError -> 404, ConflictError -> 409, InvalidInputError -> 400).
"""


class DomainError(Exception):
    """Represent a base error raised by domain operations."""

    pass


class NotFoundError(DomainError):
    """Represent a domain error for a missing entity."""

    pass


class ConflictError(DomainError):
    """Represent a domain error for a conflicting operation."""

    pass


class InvalidInputError(DomainError):
    """Represent a domain error for invalid input."""

    pass


class BookNotFoundError(NotFoundError):
    """Represent an error raised when a book cannot be found."""

    def __init__(self, book_id: int) -> None:
        """Initialize the booknotfounderror."""
        super().__init__(f"Book {book_id} not found")


class ReaderNotFoundError(NotFoundError):
    """Represent an error raised when a reader cannot be found."""

    def __init__(self, reader_id: int) -> None:
        """Initialize the readernotfounderror."""
        super().__init__(f"Reader {reader_id} not found")


class BookingNotFoundError(NotFoundError):
    """Represent an error raised when a booking cannot be found."""

    def __init__(self, booking_id: int) -> None:
        """Initialize the bookingnotfounderror."""
        super().__init__(f"Booking {booking_id} not found")


class BookAlreadyExistsError(ConflictError):
    """Represent an error for a duplicate book ISBN."""

    def __init__(self, isbn: str) -> None:
        """Initialize the bookalreadyexistserror."""
        super().__init__(f"A book with ISBN {isbn} already exists")


class IsbnBelongsToAnotherBookError(ConflictError):
    """Same ISBN but different title/author: a data error, not 'more copies'."""

    def __init__(self, isbn: str) -> None:
        """Initialize the isbnbelongstoanotherbookerror."""
        super().__init__(
            f"ISBN {isbn} is already registered with a different title or author"
        )


class NoCopiesAvailableError(ConflictError):
    """Represent an error raised when no copies are available."""

    def __init__(self, book_id: int) -> None:
        """Initialize the nocopiesavailableerror."""
        super().__init__(f"No copies of book {book_id} are available")


class CopiesInUseError(ConflictError):
    """Represent an error for reducing stock below copies on loan."""

    def __init__(self, book_id: int, on_loan: int) -> None:
        """Initialize the copiesinuseerror."""
        super().__init__(
            f"Book {book_id} has {on_loan} copies on loan; "
            "copies_total cannot go below that"
        )


class BookHasBookingsError(ConflictError):
    """Represent an error for deleting a book with booking history."""

    def __init__(self, book_id: int) -> None:
        """Initialize the bookhasbookingserror."""
        super().__init__(f"Book {book_id} has bookings and cannot be deleted")


class ReaderHasBookingsError(ConflictError):
    """Represent an error for deleting a reader with bookings."""

    def __init__(self, reader_id: int) -> None:
        """Initialize the readerhasbookingserror."""
        super().__init__(f"Reader {reader_id} has bookings and cannot be deleted")


class BookingNotActiveError(ConflictError):
    """Represent an error for changing a non-active booking."""

    def __init__(self, booking_id: int, status: str) -> None:
        """Initialize the bookingnotactiveerror."""
        super().__init__(
            f"Booking {booking_id} is {status}; only active bookings can be changed"
        )


class ReaderAlreadyExistsError(ConflictError):
    """Represent an error for a duplicate reader email."""

    def __init__(self, email: str) -> None:
        """Initialize the readeralreadyexistserror."""
        super().__init__(f"A reader with email {email} already exists")


class InvalidEmailError(InvalidInputError):
    """Represent an error raised for an invalid email address."""

    def __init__(self, email: str) -> None:
        """Initialize the invalidemailerror."""
        super().__init__(
            f"'{email}' is not a valid email address (expected name@domain.tld)"
        )


class InvalidBookingPeriodError(InvalidInputError):
    """Represent an error raised for an invalid booking period."""

    def __init__(self) -> None:
        """Initialize the invalidbookingperioderror."""
        super().__init__("end_date must not be earlier than start_date")


# Preserve the original public names for existing clients and older tests.
BookNotFound = BookNotFoundError
ReaderNotFound = ReaderNotFoundError
BookingNotFound = BookingNotFoundError
BookAlreadyExists = BookAlreadyExistsError
IsbnBelongsToAnotherBook = IsbnBelongsToAnotherBookError
NoCopiesAvailable = NoCopiesAvailableError
CopiesInUse = CopiesInUseError
BookHasBookings = BookHasBookingsError
ReaderHasBookings = ReaderHasBookingsError
BookingNotActive = BookingNotActiveError
ReaderAlreadyExists = ReaderAlreadyExistsError
InvalidEmail = InvalidEmailError
InvalidBookingPeriod = InvalidBookingPeriodError
