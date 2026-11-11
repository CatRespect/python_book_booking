"""Exercise API endpoints against the PostgreSQL test database."""

import json
from http import HTTPStatus
from typing import Protocol, cast

import pytest
from django.test import Client

client = Client()
JSON = "application/json"


class _ClientResponse(Protocol):
    """Describe the JSON-capable response interface used by these tests."""

    status_code: int

    def json(self) -> object:
        """Decode the response body as a JSON value."""
        ...


def _get(url: str) -> _ClientResponse:
    """Send a GET request and expose its JSON response interface."""
    return cast("_ClientResponse", client.get(url))


def _json_object(response: _ClientResponse) -> dict[str, object]:
    """Return a decoded JSON object from an API response."""
    return cast("dict[str, object]", response.json())


def _json_list(response: _ClientResponse) -> list[dict[str, object]]:
    """Return a decoded list of JSON objects from an API response."""
    return cast("list[dict[str, object]]", response.json())


INITIAL_COPIES = 3
RESTOCKED_COPIES = 5
COPIES_AVAILABLE_AFTER_UPDATE = 4

BOOK = {
    "title": "Clean Architecture",
    "author": "R. Martin",
    "isbn": "9780134494166",
    "copies_total": 3,
}
READER: dict[str, object] = {
    "full_name": "Jane Doe",
    "email": "jane@example.com",
}


def post(url: str, body: dict[str, object]) -> _ClientResponse:
    """Send a JSON POST request to the API."""
    return cast(
        "_ClientResponse",
        client.post(url, json.dumps(body), content_type=JSON),
    )


def make_book(**over: object) -> dict[str, object]:
    """Create a book through the API test client."""
    return _json_object(post("/api/books", {**BOOK, **over}))


def make_reader(**over: object) -> dict[str, object]:
    """Create a reader through the API test client."""
    return _json_object(post("/api/readers", {**READER, **over}))


# ---------------------------------------------------------------- books
@pytest.mark.django_db
def test_create_and_get_book() -> None:
    """Test create and get book."""
    r = post("/api/books", BOOK)
    assert r.status_code == HTTPStatus.CREATED
    created = _json_object(r)
    assert created["copies_available"] == INITIAL_COPIES
    assert created["id"]
    assert _json_object(_get(f"/api/books/{created['id']}")) == created
    assert _json_list(_get("/api/books")) == [created]


@pytest.mark.django_db
def test_book_errors() -> None:
    """Test book errors."""
    make_book()
    assert (
        post("/api/books", {**BOOK, "title": "Other"}).status_code
        == HTTPStatus.CONFLICT
    )  # ISBN, other title
    assert client.get("/api/books/999999").status_code == HTTPStatus.NOT_FOUND
    assert (
        post("/api/books", {**BOOK, "copies_total": 0}).status_code
        == HTTPStatus.UNPROCESSABLE_ENTITY
    )


# -------------------------------------------------------------- readers
@pytest.mark.django_db
def test_create_and_get_reader() -> None:
    """Test create and get reader."""
    created = post("/api/readers", READER)
    assert created.status_code == HTTPStatus.CREATED
    rid = _json_object(created)["id"]
    assert _json_object(_get(f"/api/readers/{rid}")) == {"full_name": "Jane Doe"}
    assert len(_json_list(_get("/api/readers"))) == 1


@pytest.mark.django_db
def test_reader_errors() -> None:
    """Test reader errors."""
    make_reader()
    assert (
        post("/api/readers", READER).status_code == HTTPStatus.CONFLICT
    )  # duplicate email
    assert client.get("/api/readers/999999").status_code == HTTPStatus.NOT_FOUND


# ------------------------------------------------------------- bookings
@pytest.mark.django_db
def test_create_and_get_booking() -> None:
    """Test create and get booking."""
    book, reader = make_book(), make_reader()
    body = {
        "book_id": book["id"],
        "reader_id": reader["id"],
        "start_date": "2026-01-01",
        "end_date": "2026-01-14",
    }
    r = post("/api/bookings", body)
    assert r.status_code == HTTPStatus.CREATED
    assert _json_object(r)["status"] == "active"
    got = _json_object(_get(f"/api/bookings/{_json_object(r)['id']}"))
    assert got == {**body, "status": "active"}
    assert len(_json_list(_get("/api/bookings"))) == 1


@pytest.mark.django_db
def test_booking_errors() -> None:
    """Test booking errors."""
    book, reader = make_book(), make_reader()
    ok = {
        "book_id": book["id"],
        "reader_id": reader["id"],
        "start_date": "2026-01-01",
        "end_date": "2026-01-14",
    }
    assert (
        post("/api/bookings", {**ok, "end_date": "2025-12-31"}).status_code
        == HTTPStatus.BAD_REQUEST
    )
    assert (
        post("/api/bookings", {**ok, "book_id": 999999}).status_code
        == HTTPStatus.NOT_FOUND
    )
    assert (
        post("/api/bookings", {**ok, "reader_id": 999999}).status_code
        == HTTPStatus.NOT_FOUND
    )
    assert client.get("/api/bookings/999999").status_code == HTTPStatus.NOT_FOUND


# ------------------------------------------- copies / update / delete
def booking_body(
    book: dict[str, object], reader: dict[str, object]
) -> dict[str, object]:
    """Build the request body for a booking."""
    return {
        "book_id": book["id"],
        "reader_id": reader["id"],
        "start_date": "2026-01-01",
        "end_date": "2026-01-14",
    }


def patch(url: str, body: dict[str, object]) -> _ClientResponse:
    """Send a JSON PATCH request to the API."""
    return cast(
        "_ClientResponse",
        client.patch(url, json.dumps(body), content_type=JSON),
    )


@pytest.mark.django_db
def test_booking_decrements_and_cancel_restores_copies() -> None:
    """Test booking decrements and cancel restores copies."""
    book, reader = make_book(copies_total=1), make_reader()
    r = post("/api/bookings", booking_body(book, reader))
    assert _json_object(_get(f"/api/books/{book['id']}"))["copies_available"] == 0
    assert (
        post("/api/bookings", booking_body(book, reader)).status_code
        == HTTPStatus.CONFLICT
    )
    assert (
        client.delete(f"/api/bookings/{_json_object(r)['id']}").status_code
        == HTTPStatus.NO_CONTENT
    )
    assert _json_object(_get(f"/api/books/{book['id']}"))["copies_available"] == 1
    booking_id = _json_object(r)["id"]
    assert _json_object(_get(f"/api/bookings/{booking_id}"))["status"] == "cancelled"


@pytest.mark.django_db
def test_adding_same_book_adds_copies() -> None:
    """Test adding same book adds copies."""
    first = post("/api/books", BOOK)
    again = post("/api/books", {**BOOK, "copies_total": 2})
    assert (first.status_code, again.status_code) == (HTTPStatus.CREATED, HTTPStatus.OK)
    assert _json_object(again)["copies_total"] == RESTOCKED_COPIES
    assert _json_object(again)["copies_available"] == RESTOCKED_COPIES
    assert (
        post("/api/books", {**BOOK, "title": "Other"}).status_code
        == HTTPStatus.CONFLICT
    )


@pytest.mark.django_db
def test_book_update_and_delete() -> None:
    """Test book update and delete."""
    book = make_book()
    other = make_book(isbn="222")
    url = f"/api/books/{book['id']}"
    assert _json_object(patch(url, {"title": "New"}))["title"] == "New"
    assert patch(url, {"isbn": "222"}).status_code == HTTPStatus.CONFLICT
    assert (
        patch("/api/books/999999", {"title": "x"}).status_code == HTTPStatus.NOT_FOUND
    )
    reader = make_reader()
    post("/api/bookings", booking_body(book, reader))
    assert (
        _json_object(patch(url, {"copies_total": 5}))["copies_available"]
        == COPIES_AVAILABLE_AFTER_UPDATE
    )
    assert client.delete(url).status_code == HTTPStatus.CONFLICT  # has bookings
    assert (
        client.delete(f"/api/books/{other['id']}").status_code == HTTPStatus.NO_CONTENT
    )
    assert (
        client.delete(f"/api/books/{other['id']}").status_code == HTTPStatus.NOT_FOUND
    )


@pytest.mark.django_db
def test_reader_email_validation_update_and_delete() -> None:
    """Test reader email validation update and delete."""
    assert (
        post("/api/readers", {**READER, "email": "not-an-email"}).status_code
        == HTTPStatus.BAD_REQUEST
    )
    assert (
        post("/api/readers", {**READER, "email": "a@b"}).status_code
        == HTTPStatus.BAD_REQUEST
    )
    reader = make_reader(email="Jane@Example.com")
    assert reader["email"] == "jane@example.com"
    url = f"/api/readers/{reader['id']}"
    assert patch(url, {"email": "bad"}).status_code == HTTPStatus.BAD_REQUEST
    assert _json_object(patch(url, {"full_name": "Jane Q"}))["full_name"] == "Jane Q"
    assert client.delete(url).status_code == HTTPStatus.NO_CONTENT
    assert client.delete(url).status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_booking_update_moves_copy_and_delete_rules() -> None:
    """Test booking update moves copy and delete rules."""
    b1, b2, reader = (
        make_book(copies_total=1),
        make_book(isbn="222", copies_total=1),
        make_reader(),
    )
    bid = _json_object(post("/api/bookings", booking_body(b1, reader)))["id"]
    r = patch(f"/api/bookings/{bid}", {"book_id": b2["id"], "end_date": "2026-02-01"})
    assert r.status_code == HTTPStatus.OK
    assert _json_object(r)["book_id"] == b2["id"]
    assert _json_object(_get(f"/api/books/{b1['id']}"))["copies_available"] == 1
    assert _json_object(_get(f"/api/books/{b2['id']}"))["copies_available"] == 0
    assert (
        patch(f"/api/bookings/{bid}", {"end_date": "2025-01-01"}).status_code
        == HTTPStatus.BAD_REQUEST
    )
    assert (
        patch("/api/bookings/999999", {"end_date": "2026-02-01"}).status_code
        == HTTPStatus.NOT_FOUND
    )
    client.delete(f"/api/bookings/{bid}")
    assert (
        patch(f"/api/bookings/{bid}", {"end_date": "2026-03-01"}).status_code
        == HTTPStatus.CONFLICT
    )
    assert (
        client.delete(f"/api/readers/{reader['id']}").status_code == HTTPStatus.CONFLICT
    )


def test_openapi_and_docs() -> None:
    """Test openapi and docs."""
    schema = _json_object(_get("/api/openapi.json"))
    paths = cast("dict[str, object]", schema["paths"])
    booking_path = cast("dict[str, object]", paths["/api/bookings/{booking_id}"])
    books_path = cast("dict[str, object]", paths["/api/books/{book_id}"])
    get_book = cast("dict[str, object]", books_path["get"])
    responses = cast("dict[str, object]", get_book["responses"])
    assert "delete" in booking_path
    assert "404" in responses
    assert client.get("/api/docs").status_code == HTTPStatus.OK
