"""Domain errors. Pure Python: they know nothing about HTTP.

The presentation layer maps each *category* to a status code
(NotFoundError -> 404, ConflictError -> 409, InvalidInputError -> 400).
"""


class DomainError(Exception):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class InvalidInputError(DomainError):
    pass


class BookNotFound(NotFoundError):
    def __init__(self, book_id: int):
        super().__init__(f"Book {book_id} not found")


class ReaderNotFound(NotFoundError):
    def __init__(self, reader_id: int):
        super().__init__(f"Reader {reader_id} not found")


class BookingNotFound(NotFoundError):
    def __init__(self, booking_id: int):
        super().__init__(f"Booking {booking_id} not found")


class BookAlreadyExists(ConflictError):
    def __init__(self, isbn: str):
        super().__init__(f"A book with ISBN {isbn} already exists")


class IsbnBelongsToAnotherBook(ConflictError):
    """Same ISBN but different title/author: a data error, not 'more copies'."""

    def __init__(self, isbn: str):
        super().__init__(
            f"ISBN {isbn} is already registered with a different title or author"
        )


class NoCopiesAvailable(ConflictError):
    def __init__(self, book_id: int):
        super().__init__(f"No copies of book {book_id} are available")


class CopiesInUse(ConflictError):
    def __init__(self, book_id: int, on_loan: int):
        super().__init__(
            f"Book {book_id} has {on_loan} copies on loan; copies_total cannot go below that"
        )


class BookHasBookings(ConflictError):
    def __init__(self, book_id: int):
        super().__init__(f"Book {book_id} has bookings and cannot be deleted")


class ReaderHasBookings(ConflictError):
    def __init__(self, reader_id: int):
        super().__init__(f"Reader {reader_id} has bookings and cannot be deleted")


class BookingNotActive(ConflictError):
    def __init__(self, booking_id: int, status: str):
        super().__init__(
            f"Booking {booking_id} is {status}; only active bookings can be changed"
        )


class ReaderAlreadyExists(ConflictError):
    def __init__(self, email: str):
        super().__init__(f"A reader with email {email} already exists")


class InvalidEmail(InvalidInputError):
    def __init__(self, email: str):
        super().__init__(
            f"'{email}' is not a valid email address (expected name@domain.tld)"
        )


class InvalidBookingPeriod(InvalidInputError):
    def __init__(self):
        super().__init__("end_date must not be earlier than start_date")
