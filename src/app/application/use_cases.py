"""Use cases (application layer): the business scenarios of the system.

Plain functions; the ports they need are passed in as the first arguments.
They import only from the domain and the DTOs, never from Django or the web layer.

Concurrency rule: whenever a use case reads a row and then writes a value derived from
it (copy counts, booking status), it does so inside ``uow.atomic()`` and locks the row
with ``get_for_update`` first. Otherwise two simultaneous requests could both see
"1 copy left" and both succeed.
"""

from app.application.dto import (
    BookingDetailsOutput,
    CreateBookingInput,
    CreateBookInput,
    CreateBookOutput,
    CreateReaderInput,
    ReaderNameOutput,
    UpdateBookingInput,
    UpdateBookInput,
    UpdateReaderInput,
)
from app.domain.entities import (
    Book,
    Booking,
    BookingStatus,
    NewBook,
    NewBooking,
    NewReader,
    Reader,
)
from app.domain.exceptions import (
    BookAlreadyExists,
    BookHasBookings,
    BookingNotActive,
    BookingNotFound,
    BookNotFound,
    InvalidBookingPeriod,
    InvalidEmail,
    IsbnBelongsToAnotherBook,
    ReaderHasBookings,
    ReaderNotFound,
)
from app.domain.repositories import (
    BookingRepository,
    BookRepository,
    ReaderRepository,
    UnitOfWork,
)
from app.domain.validators import is_valid_email, normalize_email


def _checked_email(raw: str) -> str:
    email = normalize_email(raw)
    if not is_valid_email(email):
        raise InvalidEmail(raw)
    return email


# ---------------------------------------------------------------- books
def list_books(books: BookRepository) -> list[Book]:
    return books.list()


def get_book(books: BookRepository, book_id: int) -> Book:
    book = books.get(book_id)
    if book is None:
        raise BookNotFound(book_id)
    return book


def create_book(
    books: BookRepository, uow: UnitOfWork, data: CreateBookInput
) -> CreateBookOutput:
    """Add a new title, or add copies to an existing one.

    * ISBN unknown                         -> new book, all copies available (created=True)
    * ISBN known, same title and author    -> copies_total and copies_available both grow
                                              by data.copies_total (created=False)
    * ISBN known, different title/author   -> IsbnBelongsToAnotherBook (409)
    """
    with uow.atomic():
        existing = books.get_by_isbn(data.isbn)
        if existing is None:
            try:
                new = NewBook(
                    title=data.title,
                    author=data.author,
                    isbn=data.isbn,
                    copies_total=data.copies_total,
                    copies_available=data.copies_total,
                )
                return CreateBookOutput(book=books.add(new), created=True)
            except BookAlreadyExists:
                # Another request created this ISBN between our lookup and our insert.
                existing = books.get_by_isbn(data.isbn)
                if existing is None:  # pragma: no cover - vanished again: report as is
                    raise
        # Lock the row so that concurrent "add copies" requests do not overwrite
        # each other, then re-check against the locked (fresh) values.
        locked = books.get_for_update(existing.id)
        if locked is None:  # pragma: no cover - deleted in between
            raise BookNotFound(existing.id)
        if not locked.is_same_edition(data.title, data.author):
            raise IsbnBelongsToAnotherBook(data.isbn)
        updated = books.save(locked.with_copies_added(data.copies_total))
        return CreateBookOutput(book=updated, created=False)


def update_book(
    books: BookRepository, uow: UnitOfWork, book_id: int, data: UpdateBookInput
) -> Book:
    changes = data.model_dump(exclude_none=True)  # null in a PATCH means "not sent"
    with uow.atomic():
        book = books.get_for_update(book_id)
        if book is None:
            raise BookNotFound(book_id)
        new_total = changes.pop("copies_total", None)
        if new_total is not None:
            book = book.with_total_copies(new_total)  # may raise CopiesInUse
        book = book.model_copy(update=changes)
        return books.save(book)  # may raise BookAlreadyExists (ISBN taken)


def remove_book(
    books: BookRepository, bookings: BookingRepository, uow: UnitOfWork, book_id: int
) -> None:
    with uow.atomic():
        if books.get_for_update(book_id) is None:
            raise BookNotFound(book_id)
        # Bookings (even cancelled ones) are history that points at the book.
        if bookings.exists_for_book(book_id):
            raise BookHasBookings(book_id)
        books.delete(book_id)


# -------------------------------------------------------------- readers
def list_readers(readers: ReaderRepository) -> list[Reader]:
    return readers.list()


def get_reader(readers: ReaderRepository, reader_id: int) -> ReaderNameOutput:
    reader = readers.get(reader_id)
    if reader is None:
        raise ReaderNotFound(reader_id)
    return ReaderNameOutput(full_name=reader.full_name)


def create_reader(readers: ReaderRepository, data: CreateReaderInput) -> Reader:
    email = _checked_email(data.email)
    return readers.add(NewReader(full_name=data.full_name, email=email))


def update_reader(
    readers: ReaderRepository, reader_id: int, data: UpdateReaderInput
) -> Reader:
    changes = data.model_dump(exclude_none=True)
    if "email" in changes:
        changes["email"] = _checked_email(changes["email"])
    reader = readers.get(reader_id)
    if reader is None:
        raise ReaderNotFound(reader_id)
    return readers.save(reader.model_copy(update=changes))


def remove_reader(
    readers: ReaderRepository, bookings: BookingRepository, reader_id: int
) -> None:
    if readers.get(reader_id) is None:
        raise ReaderNotFound(reader_id)
    if bookings.exists_for_reader(reader_id):
        raise ReaderHasBookings(reader_id)
    readers.delete(reader_id)


# ------------------------------------------------------------- bookings
def list_bookings(bookings: BookingRepository) -> list[Booking]:
    return bookings.list()


def get_booking(bookings: BookingRepository, booking_id: int) -> BookingDetailsOutput:
    booking = bookings.get(booking_id)
    if booking is None:
        raise BookingNotFound(booking_id)
    return BookingDetailsOutput(**booking.model_dump(exclude={"id"}))


def create_booking(
    bookings: BookingRepository,
    books: BookRepository,
    readers: ReaderRepository,
    uow: UnitOfWork,
    data: CreateBookingInput,
) -> Booking:
    """Book one copy: checks the rules, takes a copy, stores the booking - atomically."""
    if data.end_date < data.start_date:
        raise InvalidBookingPeriod
    with uow.atomic():
        book = books.get_for_update(data.book_id)
        if book is None:
            raise BookNotFound(data.book_id)
        if readers.get(data.reader_id) is None:
            raise ReaderNotFound(data.reader_id)
        books.save(book.with_copy_taken())  # raises NoCopiesAvailable at 0
        return bookings.add(NewBooking(**data.model_dump()))


def update_booking(
    bookings: BookingRepository,
    books: BookRepository,
    readers: ReaderRepository,
    uow: UnitOfWork,
    booking_id: int,
    data: UpdateBookingInput,
) -> Booking:
    """Change dates, reader or book of an ACTIVE booking.

    Moving a booking to another book returns the copy of the old book and takes one
    from the new book. Nothing is written unless every check passes.
    """
    changes = data.model_dump(exclude_none=True)
    with uow.atomic():
        booking = bookings.get_for_update(booking_id)
        if booking is None:
            raise BookingNotFound(booking_id)
        if booking.status != BookingStatus.ACTIVE:
            raise BookingNotActive(booking_id, booking.status.value)

        updated = booking.model_copy(update=changes)
        if updated.end_date < updated.start_date:
            raise InvalidBookingPeriod
        if (
            updated.reader_id != booking.reader_id
            and readers.get(updated.reader_id) is None
        ):
            raise ReaderNotFound(updated.reader_id)

        if updated.book_id != booking.book_id:
            _move_copy(books, old_id=booking.book_id, new_id=updated.book_id)
        return bookings.save(updated)


def _move_copy(books: BookRepository, old_id: int, new_id: int) -> None:
    # Lock in ascending id order: two requests moving bookings in opposite
    # directions between the same two books would otherwise deadlock.
    locked: dict[int, Book | None] = {
        i: books.get_for_update(i) for i in sorted({old_id, new_id})
    }
    old, new = locked[old_id], locked[new_id]
    if new is None:
        raise BookNotFound(new_id)
    if old is None:  # pragma: no cover - FK PROTECT makes this impossible
        raise BookNotFound(old_id)
    taken = new.with_copy_taken()  # raises NoCopiesAvailable
    books.save(taken)
    books.save(old.with_copy_returned())


def remove_booking(
    bookings: BookingRepository,
    books: BookRepository,
    uow: UnitOfWork,
    booking_id: int,
) -> None:
    """Soft delete: the booking becomes CANCELLED and its copy becomes available again.

    DELETE is idempotent: cancelling an already cancelled booking does nothing.
    A RETURNED booking is history and cannot be cancelled.
    """
    with uow.atomic():
        booking = bookings.get_for_update(booking_id)
        if booking is None:
            raise BookingNotFound(booking_id)
        if booking.status == BookingStatus.CANCELLED:
            return
        if booking.status != BookingStatus.ACTIVE:
            raise BookingNotActive(booking_id, booking.status.value)
        book = books.get_for_update(booking.book_id)
        if book is not None:
            books.save(book.with_copy_returned())
        bookings.save(booking.model_copy(update={"status": BookingStatus.CANCELLED}))
