"""In-memory repositories: let use cases be tested with NO database."""
from app.domain.entities import Book, Booking, NewBook, NewBooking, NewReader, Reader
from app.domain.exceptions import BookAlreadyExists, ReaderAlreadyExists
from app.domain.repositories import BookingRepository, BookRepository, ReaderRepository


class FakeBookRepository(BookRepository):
    def __init__(self):
        self.items: dict[int, Book] = {}

    def list(self):
        return list(self.items.values())

    def get(self, book_id):
        return self.items.get(book_id)

    def add(self, new_book: NewBook):
        if any(b.isbn == new_book.isbn for b in self.items.values()):
            raise BookAlreadyExists(new_book.isbn)
        book = Book(id=len(self.items) + 1, **new_book.model_dump())
        self.items[book.id] = book
        return book


class FakeReaderRepository(ReaderRepository):
    def __init__(self):
        self.items: dict[int, Reader] = {}

    def list(self):
        return list(self.items.values())

    def get(self, reader_id):
        return self.items.get(reader_id)

    def add(self, new_reader: NewReader):
        if any(r.email == new_reader.email for r in self.items.values()):
            raise ReaderAlreadyExists(new_reader.email)
        reader = Reader(id=len(self.items) + 1, **new_reader.model_dump())
        self.items[reader.id] = reader
        return reader


class FakeBookingRepository(BookingRepository):
    def __init__(self):
        self.items: dict[int, Booking] = {}

    def list(self):
        return list(self.items.values())

    def get(self, booking_id):
        return self.items.get(booking_id)

    def add(self, new_booking: NewBooking):
        booking = Booking(id=len(self.items) + 1, **new_booking.model_dump())
        self.items[booking.id] = booking
        return booking
