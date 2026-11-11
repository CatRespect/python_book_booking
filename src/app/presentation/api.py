"""Python module for api."""

from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI, Router, Schema, Status

from app.application import use_cases
from app.application.dto import (
    BookingDetailsOutput,
    CreateBookingInput,
    CreateBookInput,
    CreateReaderInput,
    ReaderNameOutput,
    UpdateBookingInput,
    UpdateBookInput,
    UpdateReaderInput,
)
from app.domain.entities import Book, Booking, Reader
from app.domain.exceptions import ConflictError, InvalidInputError, NotFoundError
from config import container

api = NinjaAPI(
    title="Book Booking API",
    version="0.3.0",
    description=(
        "Full CRUD backed by PostgreSQL, with copy availability tracking. "
        "Booking takes a copy; cancelling returns it; re-adding a book with the same "
        "ISBN, title and author adds copies."
    ),
)


class ErrorResponse(Schema):
    """Represent a structured API error response."""

    detail: str


# Map domain errors to HTTP statuses; the domain itself knows nothing about HTTP.
@api.exception_handler(NotFoundError)
def handle_not_found(request: HttpRequest, exc: NotFoundError) -> HttpResponse:
    """Convert a not-found domain error into an HTTP response."""
    return api.create_response(request, {"detail": str(exc)}, status=404)


@api.exception_handler(ConflictError)
def handle_conflict(request: HttpRequest, exc: ConflictError) -> HttpResponse:
    """Convert a conflict domain error into an HTTP response."""
    return api.create_response(request, {"detail": str(exc)}, status=409)


@api.exception_handler(InvalidInputError)
def handle_invalid_input(request: HttpRequest, exc: InvalidInputError) -> HttpResponse:
    """Convert an invalid-input domain error into an HTTP response."""
    return api.create_response(request, {"detail": str(exc)}, status=400)


books = Router(tags=["Books"])
readers = Router(tags=["Readers"])
bookings = Router(tags=["Bookings"])


# ---- Books ----
@books.get("", response=list[Book], summary="List books")
def get_books(request: HttpRequest) -> list[Book]:
    """List all books."""
    _ = request  # Django Ninja injects this framework argument.
    return use_cases.list_books(container.book_repository())


@books.get("/{book_id}", response={200: Book, 404: ErrorResponse}, summary="Get a book")
def get_book(request: HttpRequest, book_id: int) -> Book:
    """Get a book by its identifier."""
    _ = request  # Django Ninja injects this framework argument.
    return use_cases.get_book(container.book_repository(), book_id)


@books.post(
    "",
    response={201: Book, 200: Book, 409: ErrorResponse},
    summary="Create a book, or add copies to an existing one",
    description=(
        "201: a new book was created. "
        "200: a book with the same ISBN, title and author already existed, so "
        "`copies_total` copies were added to its total and available counts. "
        "409: the ISBN exists with a different title or author."
    ),
)
def post_book(request: HttpRequest, payload: CreateBookInput) -> Status:
    """Create a book or add copies to an existing book."""
    _ = request  # Django Ninja injects this framework argument.
    result = use_cases.create_book(
        container.book_repository(), container.unit_of_work(), payload
    )
    return Status(201 if result.created else 200, result.book)


@books.patch(
    "/{book_id}",
    response={200: Book, 404: ErrorResponse, 409: ErrorResponse},
    summary="Update a book",
    description=(
        "`copies_total` is the new total stock; copies on loan are kept, so "
        "`copies_available` is recomputed. 409 if it would drop below the copies on "
        "loan, or if the new ISBN belongs to another book."
    ),
)
def patch_book(request: HttpRequest, book_id: int, payload: UpdateBookInput) -> Book:
    """Update a book."""
    _ = request  # Django Ninja injects this framework argument.
    return use_cases.update_book(
        container.book_repository(), container.unit_of_work(), book_id, payload
    )


@books.delete(
    "/{book_id}",
    response={204: None, 404: ErrorResponse, 409: ErrorResponse},
    summary="Delete a book",
    description="409 if the book has any bookings (including cancelled ones).",
)
def delete_book(request: HttpRequest, book_id: int) -> Status:
    """Delete a book without booking history."""
    _ = request  # Django Ninja injects this framework argument.
    use_cases.remove_book(
        container.book_repository(),
        container.booking_repository(),
        container.unit_of_work(),
        book_id,
    )
    return Status(204, None)


# ---- Readers ----
@readers.get("", response=list[Reader], summary="List readers")
def get_readers(request: HttpRequest) -> list[Reader]:
    """List all readers."""
    _ = request  # Django Ninja injects this framework argument.
    return use_cases.list_readers(container.reader_repository())


@readers.get(
    "/{reader_id}",
    response={200: ReaderNameOutput, 404: ErrorResponse},
    summary="Get a reader's name",
)
def get_reader(request: HttpRequest, reader_id: int) -> ReaderNameOutput:
    """Get a reader by its identifier."""
    _ = request  # Django Ninja injects this framework argument.
    return use_cases.get_reader(container.reader_repository(), reader_id)


@readers.post(
    "",
    response={201: Reader, 400: ErrorResponse, 409: ErrorResponse},
    summary="Create a reader",
)
def post_reader(request: HttpRequest, payload: CreateReaderInput) -> Status:
    """Create a reader."""
    _ = request  # Django Ninja injects this framework argument.
    return Status(201, use_cases.create_reader(container.reader_repository(), payload))


@readers.patch(
    "/{reader_id}",
    response={
        200: Reader,
        400: ErrorResponse,
        404: ErrorResponse,
        409: ErrorResponse,
    },
    summary="Update a reader",
)
def patch_reader(
    request: HttpRequest, reader_id: int, payload: UpdateReaderInput
) -> Reader:
    """Update a reader."""
    _ = request  # Django Ninja injects this framework argument.
    return use_cases.update_reader(container.reader_repository(), reader_id, payload)


@readers.delete(
    "/{reader_id}",
    response={204: None, 404: ErrorResponse, 409: ErrorResponse},
    summary="Delete a reader",
    description="409 if the reader has any bookings (including cancelled ones).",
)
def delete_reader(request: HttpRequest, reader_id: int) -> Status:
    """Delete a reader without booking history."""
    _ = request  # Django Ninja injects this framework argument.
    use_cases.remove_reader(
        container.reader_repository(), container.booking_repository(), reader_id
    )
    return Status(204, None)


# ---- Bookings ----
@bookings.get("", response=list[Booking], summary="List bookings")
def get_bookings(request: HttpRequest) -> list[Booking]:
    """List all bookings."""
    _ = request  # Django Ninja injects this framework argument.
    return use_cases.list_bookings(container.booking_repository())


@bookings.get(
    "/{booking_id}",
    response={200: BookingDetailsOutput, 404: ErrorResponse},
    summary="Get a booking",
)
def get_booking(request: HttpRequest, booking_id: int) -> BookingDetailsOutput:
    """Get a booking by its identifier."""
    _ = request  # Django Ninja injects this framework argument.
    return use_cases.get_booking(container.booking_repository(), booking_id)


@bookings.post(
    "",
    response={
        201: Booking,
        400: ErrorResponse,
        404: ErrorResponse,
        409: ErrorResponse,
    },
    summary="Create a booking",
    description="Takes one copy of the book. 409 if no copies are available.",
)
def post_booking(request: HttpRequest, payload: CreateBookingInput) -> Status:
    """Create a booking and reserve one copy."""
    _ = request  # Django Ninja injects this framework argument.
    booking = use_cases.create_booking(
        container.booking_repository(),
        container.book_repository(),
        container.reader_repository(),
        container.unit_of_work(),
        payload,
    )
    return Status(201, booking)


@bookings.patch(
    "/{booking_id}",
    response={
        200: Booking,
        400: ErrorResponse,
        404: ErrorResponse,
        409: ErrorResponse,
    },
    summary="Update a booking",
    description=(
        "Only active bookings can be changed (409 otherwise). Moving a booking to "
        "another book returns the old copy and takes one from the new book "
        "(409 if none is available)."
    ),
)
def patch_booking(
    request: HttpRequest, booking_id: int, payload: UpdateBookingInput
) -> Booking:
    """Update an active booking."""
    _ = request  # Django Ninja injects this framework argument.
    return use_cases.update_booking(
        container.booking_repository(),
        container.book_repository(),
        container.reader_repository(),
        container.unit_of_work(),
        booking_id,
        payload,
    )


@bookings.delete(
    "/{booking_id}",
    response={204: None, 404: ErrorResponse, 409: ErrorResponse},
    summary="Cancel a booking",
    description=(
        "Soft delete: status becomes `cancelled` and the copy becomes available "
        "again. Repeating the call is harmless. 409 for a returned booking."
    ),
)
def delete_booking(request: HttpRequest, booking_id: int) -> Status:
    """Cancel a booking and return its copy."""
    _ = request  # Django Ninja injects this framework argument.
    use_cases.remove_booking(
        container.booking_repository(),
        container.book_repository(),
        container.unit_of_work(),
        booking_id,
    )
    return Status(204, None)


api.add_router("/books", books)
api.add_router("/readers", readers)
api.add_router("/bookings", bookings)
