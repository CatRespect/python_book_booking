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


class ReaderAlreadyExists(ConflictError):
    def __init__(self, email: str):
        super().__init__(f"A reader with email {email} already exists")


class InvalidBookingPeriod(InvalidInputError):
    def __init__(self):
        super().__init__("end_date must not be earlier than start_date")
