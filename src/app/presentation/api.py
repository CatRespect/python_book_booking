from ninja import NinjaAPI, Router, Status

from app.application import use_cases
from app.application.dto import CreateBookingInput, CreateBookInput, CreateReaderInput
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


# ---- Readers ----
@readers.get("", response=list[Reader], summary="List readers")
def get_readers(request):
    return use_cases.list_readers()


@readers.post("", response={201: Reader}, summary="Create a reader")
def post_reader(request, payload: CreateReaderInput):
    return Status(201, use_cases.create_reader(payload))


# ---- Bookings ----
@bookings.get("", response=list[Booking], summary="List bookings")
def get_bookings(request):
    return use_cases.list_bookings()


@bookings.post("", response={201: Booking}, summary="Create a booking")
def post_booking(request, payload: CreateBookingInput):
    return Status(201, use_cases.create_booking(payload))


@bookings.post("/{booking_id}/cancel", response=Booking, summary="Cancel a booking")
def cancel_booking(request, booking_id: int):
    return use_cases.cancel_booking(booking_id)


api.add_router("/books", books)
api.add_router("/readers", readers)
api.add_router("/bookings", bookings)
