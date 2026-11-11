from ninja import NinjaAPI, Router, Status

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

api = NinjaAPI(
    title="Book Booking API",
    version="0.1.0",
    description="Prototype: endpoints return stub data, no business logic yet.",
)

books = Router(tags=["Books"])
readers = Router(tags=["Readers"])
bookings = Router(tags=["Bookings"])


# ---- Books ----
@books.get("", response=list[Book], summary="List books")
def get_books(request):
    return use_cases.list_books()


@books.get("/{book_id}", response=Book, summary="Get a book")
def get_book(request, book_id: int):
    return use_cases.get_book(book_id)


@books.post("", response={201: Book}, summary="Create a book")
def post_book(request, payload: CreateBookInput):
    return Status(201, use_cases.create_book(payload))


@books.patch("/{book_id}", response=Book, summary="Update a book")
def patch_book(request, book_id: int, payload: UpdateBookInput):
    return use_cases.update_book(book_id, payload)


@books.delete("/{book_id}", response={204: None}, summary="Remove a book")
def delete_book(request, book_id: int):
    use_cases.remove_book(book_id)
    return Status(204, None)


# ---- Readers ----
@readers.get("", response=list[Reader], summary="List readers")
def get_readers(request):
    return use_cases.list_readers()


@readers.get("/{reader_id}", response=ReaderNameOutput, summary="Get a reader's name")
def get_reader(request, reader_id: int):
    return use_cases.get_reader(reader_id)


@readers.post("", response={201: Reader}, summary="Create a reader")
def post_reader(request, payload: CreateReaderInput):
    return Status(201, use_cases.create_reader(payload))


@readers.patch("/{reader_id}", response=Reader, summary="Update a reader")
def patch_reader(request, reader_id: int, payload: UpdateReaderInput):
    return use_cases.update_reader(reader_id, payload)


@readers.delete("/{reader_id}", response={204: None}, summary="Remove a reader")
def delete_reader(request, reader_id: int):
    use_cases.remove_reader(reader_id)
    return Status(204, None)


# ---- Bookings ----
@bookings.get("", response=list[Booking], summary="List bookings")
def get_bookings(request):
    return use_cases.list_bookings()


@bookings.get("/{booking_id}", response=BookingDetailsOutput, summary="Get a booking")
def get_booking(request, booking_id: int):
    return use_cases.get_booking(booking_id)


@bookings.post("", response={201: Booking}, summary="Create a booking")
def post_booking(request, payload: CreateBookingInput):
    return Status(201, use_cases.create_booking(payload))


@bookings.patch("/{booking_id}", response=Booking, summary="Update a booking")
def patch_booking(request, booking_id: int, payload: UpdateBookingInput):
    return use_cases.update_booking(booking_id, payload)


@bookings.delete("/{booking_id}", response={204: None}, summary="Remove (cancel) a booking")
def delete_booking(request, booking_id: int):
    use_cases.remove_booking(booking_id)
    return Status(204, None)


api.add_router("/books", books)
api.add_router("/readers", readers)
api.add_router("/bookings", bookings)
