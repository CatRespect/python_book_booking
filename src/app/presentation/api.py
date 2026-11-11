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
    version="0.2.0",
    description=(
        "List / get / create are backed by PostgreSQL. "
        "PATCH and DELETE are still stubs returning sample data."
    ),
)


class ErrorResponse(Schema):
    detail: str


# ---- domain error category -> HTTP status (the domain itself knows nothing about HTTP) ----
@api.exception_handler(NotFoundError)
def handle_not_found(request, exc):
    return api.create_response(request, {"detail": str(exc)}, status=404)


@api.exception_handler(ConflictError)
def handle_conflict(request, exc):
    return api.create_response(request, {"detail": str(exc)}, status=409)


@api.exception_handler(InvalidInputError)
def handle_invalid_input(request, exc):
    return api.create_response(request, {"detail": str(exc)}, status=400)


books = Router(tags=["Books"])
readers = Router(tags=["Readers"])
bookings = Router(tags=["Bookings"])


# ---- Books ----
@books.get("", response=list[Book], summary="List books")
def get_books(request):
    return use_cases.list_books(container.book_repository())


@books.get("/{book_id}", response={200: Book, 404: ErrorResponse}, summary="Get a book")
def get_book(request, book_id: int):
    return use_cases.get_book(container.book_repository(), book_id)


@books.post("", response={201: Book, 409: ErrorResponse}, summary="Create a book")
def post_book(request, payload: CreateBookInput):
    return Status(201, use_cases.create_book(container.book_repository(), payload))


@books.patch("/{book_id}", response=Book, summary="Update a book (stub)")
def patch_book(request, book_id: int, payload: UpdateBookInput):
    return use_cases.update_book(book_id, payload)


@books.delete("/{book_id}", response={204: None}, summary="Remove a book (stub)")
def delete_book(request, book_id: int):
    use_cases.remove_book(book_id)
    return Status(204, None)


# ---- Readers ----
@readers.get("", response=list[Reader], summary="List readers")
def get_readers(request):
    return use_cases.list_readers(container.reader_repository())


@readers.get(
    "/{reader_id}",
    response={200: ReaderNameOutput, 404: ErrorResponse},
    summary="Get a reader's name",
)
def get_reader(request, reader_id: int):
    return use_cases.get_reader(container.reader_repository(), reader_id)


@readers.post("", response={201: Reader, 409: ErrorResponse}, summary="Create a reader")
def post_reader(request, payload: CreateReaderInput):
    return Status(201, use_cases.create_reader(container.reader_repository(), payload))


@readers.patch("/{reader_id}", response=Reader, summary="Update a reader (stub)")
def patch_reader(request, reader_id: int, payload: UpdateReaderInput):
    return use_cases.update_reader(reader_id, payload)


@readers.delete("/{reader_id}", response={204: None}, summary="Remove a reader (stub)")
def delete_reader(request, reader_id: int):
    use_cases.remove_reader(reader_id)
    return Status(204, None)


# ---- Bookings ----
@bookings.get("", response=list[Booking], summary="List bookings")
def get_bookings(request):
    return use_cases.list_bookings(container.booking_repository())


@bookings.get(
    "/{booking_id}",
    response={200: BookingDetailsOutput, 404: ErrorResponse},
    summary="Get a booking",
)
def get_booking(request, booking_id: int):
    return use_cases.get_booking(container.booking_repository(), booking_id)


@bookings.post(
    "",
    response={201: Booking, 400: ErrorResponse, 404: ErrorResponse},
    summary="Create a booking",
)
def post_booking(request, payload: CreateBookingInput):
    booking = use_cases.create_booking(
        container.booking_repository(),
        container.book_repository(),
        container.reader_repository(),
        payload,
    )
    return Status(201, booking)


@bookings.patch("/{booking_id}", response=Booking, summary="Update a booking (stub)")
def patch_booking(request, booking_id: int, payload: UpdateBookingInput):
    return use_cases.update_booking(booking_id, payload)


@bookings.delete(
    "/{booking_id}", response={204: None}, summary="Remove (cancel) a booking (stub)"
)
def delete_booking(request, booking_id: int):
    use_cases.remove_booking(booking_id)
    return Status(204, None)


api.add_router("/books", books)
api.add_router("/readers", readers)
api.add_router("/bookings", bookings)
