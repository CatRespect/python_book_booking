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
    BookAlreadyExistsError,
    BookHasBookingsError,
    BookingNotActiveError,
    BookingNotFoundError,
    BookNotFoundError,
    InvalidBookingPeriodError,
    InvalidEmailError,
    IsbnBelongsToAnotherBookError,
    ReaderHasBookingsError,
    ReaderNotFoundError,
)
from app.domain.repositories import (
    BookingRepository,
    BookRepository,
    ReaderRepository,
    UnitOfWork,
)
from app.domain.validators import is_valid_email, normalize_email


def _checked_email(raw: str) -> str:
    """Normalize and validate an email address."""
    email = normalize_email(raw)
    if not is_valid_email(email):
        raise InvalidEmailError(raw)
    return email


# ---------------------------------------------------------------- books
def list_books(books: BookRepository) -> list[Book]:
    """List all books."""
    return books.list()


def get_book(books: BookRepository, book_id: int) -> Book:
    """Get a book by its identifier."""
    book = books.get(book_id)
    if book is None:
        raise BookNotFoundError(book_id)
    return book


def create_book(
    books: BookRepository, uow: UnitOfWork, data: CreateBookInput
) -> CreateBookOutput:
    """Add a new title, or add copies to an existing one.

    * Unknown ISBN: create a book with all copies available (``created=True``).
    * Matching ISBN, title, and author: add the requested copies (``created=False``).
    * ISBN known, different title/author   -> IsbnBelongsToAnotherBookError (409)
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
            except BookAlreadyExistsError:
                # Another request created this ISBN between our lookup and our insert.
                existing = books.get_by_isbn(data.isbn)
                if existing is None:  # pragma: no cover - vanished again: report as is
                    raise
        # Lock the row so that concurrent "add copies" requests do not overwrite
        # each other, then re-check against the locked (fresh) values.
        locked = books.get_for_update(existing.id)
        if locked is None:  # pragma: no cover - deleted in between
            raise BookNotFoundError(existing.id)
        if not locked.is_same_edition(data.title, data.author):
            raise IsbnBelongsToAnotherBookError(data.isbn)
        updated = books.save(locked.with_copies_added(data.copies_total))
        return CreateBookOutput(book=updated, created=False)


def update_book(
    books: BookRepository, uow: UnitOfWork, book_id: int, data: UpdateBookInput
) -> Book:
    """Update a book and its stock information."""
    changes = data.model_dump(exclude_none=True)  # null in a PATCH means "not sent"
    with uow.atomic():
        book = books.get_for_update(book_id)
        if book is None:
            raise BookNotFoundError(book_id)
        new_total = changes.pop("copies_total", None)
        if new_total is not None:
            book = book.with_total_copies(new_total)  # may raise CopiesInUseError
        book = book.model_copy(update=changes)
        return books.save(book)  # may raise BookAlreadyExistsError (ISBN taken)


def remove_book(
    books: BookRepository, bookings: BookingRepository, uow: UnitOfWork, book_id: int
) -> None:
    """Remove a book that has no booking history."""
    with uow.atomic():
        if books.get_for_update(book_id) is None:
            raise BookNotFoundError(book_id)
        # Bookings (even cancelled ones) are history that points at the book.
        if bookings.exists_for_book(book_id):
            raise BookHasBookingsError(book_id)
        books.delete(book_id)


# -------------------------------------------------------------- readers
def list_readers(readers: ReaderRepository) -> list[Reader]:
    """List all readers."""
    return readers.list()


def get_reader(readers: ReaderRepository, reader_id: int) -> ReaderNameOutput:
    """Get a reader by its identifier."""
    reader = readers.get(reader_id)
    if reader is None:
        raise ReaderNotFoundError(reader_id)
    return ReaderNameOutput(full_name=reader.full_name)


def create_reader(readers: ReaderRepository, data: CreateReaderInput) -> Reader:
    """Create a reader after validating the email address."""
    email = _checked_email(data.email)
    return readers.add(NewReader(full_name=data.full_name, email=email))


def update_reader(
    readers: ReaderRepository, reader_id: int, data: UpdateReaderInput
) -> Reader:
    """Update a reader and validate a changed email address."""
    changes = data.model_dump(exclude_none=True)
    if "email" in changes:
        changes["email"] = _checked_email(changes["email"])
    reader = readers.get(reader_id)
    if reader is None:
        raise ReaderNotFoundError(reader_id)
    return readers.save(reader.model_copy(update=changes))


def remove_reader(
    readers: ReaderRepository, bookings: BookingRepository, reader_id: int
) -> None:
    """Remove a reader who has no bookings."""
    if readers.get(reader_id) is None:
        raise ReaderNotFoundError(reader_id)
    if bookings.exists_for_reader(reader_id):
        raise ReaderHasBookingsError(reader_id)
    readers.delete(reader_id)


# ------------------------------------------------------------- bookings
def list_bookings(bookings: BookingRepository) -> list[Booking]:
    """List all bookings."""
    return bookings.list()


def get_booking(bookings: BookingRepository, booking_id: int) -> BookingDetailsOutput:
    """Get a booking by its identifier."""
    booking = bookings.get(booking_id)
    if booking is None:
        raise BookingNotFoundError(booking_id)
    return BookingDetailsOutput(**booking.model_dump(exclude={"id"}))


def create_booking(
    bookings: BookingRepository,
    books: BookRepository,
    readers: ReaderRepository,
    uow: UnitOfWork,
    data: CreateBookingInput,
) -> Booking:
    """Reserve one copy atomically.

    Validate the booking, reserve a copy, and store the booking.
    """
    if data.end_date < data.start_date:
        raise InvalidBookingPeriodError
    with uow.atomic():
        book = books.get_for_update(data.book_id)
        if book is None:
            raise BookNotFoundError(data.book_id)
        if readers.get(data.reader_id) is None:
            raise ReaderNotFoundError(data.reader_id)
        books.save(book.with_copy_taken())  # raises NoCopiesAvailableError at 0
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
            raise BookingNotFoundError(booking_id)
        if booking.status != BookingStatus.ACTIVE:
            raise BookingNotActiveError(booking_id, booking.status.value)

        updated = booking.model_copy(update=changes)
        if updated.end_date < updated.start_date:
            raise InvalidBookingPeriodError
        if (
            updated.reader_id != booking.reader_id
            and readers.get(updated.reader_id) is None
        ):
            raise ReaderNotFoundError(updated.reader_id)

        if updated.book_id != booking.book_id:
            _move_copy(books, old_id=booking.book_id, new_id=updated.book_id)
        return bookings.save(updated)


def _move_copy(books: BookRepository, old_id: int, new_id: int) -> None:
    # Lock in ascending id order: two requests moving bookings in opposite
    # directions between the same two books would otherwise deadlock.
    """Move the reserved copy between books."""
    locked: dict[int, Book | None] = {
        i: books.get_for_update(i) for i in sorted({old_id, new_id})
    }
    old, new = locked[old_id], locked[new_id]
    if new is None:
        raise BookNotFoundError(new_id)
    if old is None:  # pragma: no cover - FK PROTECT makes this impossible
        raise BookNotFoundError(old_id)
    taken = new.with_copy_taken()  # raises NoCopiesAvailableError
    books.save(taken)
    books.save(old.with_copy_returned())


def remove_booking(
    bookings: BookingRepository,
    books: BookRepository,
    uow: UnitOfWork,
    booking_id: int,
) -> None:
    """Cancel a booking and make its reserved copy available again.

    DELETE is idempotent: cancelling an already cancelled booking does nothing.
    A RETURNED booking is history and cannot be cancelled.
    """
    with uow.atomic():
        booking = bookings.get_for_update(booking_id)
        if booking is None:
            raise BookingNotFoundError(booking_id)
        if booking.status == BookingStatus.CANCELLED:
            return
        if booking.status != BookingStatus.ACTIVE:
            raise BookingNotActiveError(booking_id, booking.status.value)
        book = books.get_for_update(booking.book_id)
        if book is not None:
            books.save(book.with_copy_returned())
        bookings.save(booking.model_copy(update={"status": BookingStatus.CANCELLED}))
