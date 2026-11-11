"""API tests. Implemented endpoints hit the real PostgreSQL test database (make db-up first)."""

import json

import pytest
from django.test import Client

client = Client()
JSON = "application/json"

BOOK = {
    "title": "Clean Architecture",
    "author": "R. Martin",
    "isbn": "9780134494166",
    "copies_total": 3,
}
READER = {"full_name": "Jane Doe", "email": "jane@example.com"}


def post(url, body):
    return client.post(url, json.dumps(body), content_type=JSON)


def make_book(**over):
    return post("/api/books", {**BOOK, **over}).json()


def make_reader(**over):
    return post("/api/readers", {**READER, **over}).json()


# ---------------------------------------------------------------- books
@pytest.mark.django_db
def test_create_and_get_book() -> None:
    r = post("/api/books", BOOK)
    assert r.status_code == 201
    created = r.json()
    assert created["copies_available"] == 3
    assert created["id"]
    assert client.get(f"/api/books/{created['id']}").json() == created
    assert client.get("/api/books").json() == [created]


@pytest.mark.django_db
def test_book_errors() -> None:
    make_book()
    assert (
        post("/api/books", {**BOOK, "title": "Other"}).status_code == 409
    )  # ISBN, other title
    assert client.get("/api/books/999999").status_code == 404
    assert post("/api/books", {**BOOK, "copies_total": 0}).status_code == 422


# -------------------------------------------------------------- readers
@pytest.mark.django_db
def test_create_and_get_reader() -> None:
    created = post("/api/readers", READER)
    assert created.status_code == 201
    rid = created.json()["id"]
    assert client.get(f"/api/readers/{rid}").json() == {"full_name": "Jane Doe"}
    assert len(client.get("/api/readers").json()) == 1


@pytest.mark.django_db
def test_reader_errors() -> None:
    make_reader()
    assert post("/api/readers", READER).status_code == 409  # duplicate email
    assert client.get("/api/readers/999999").status_code == 404


# ------------------------------------------------------------- bookings
@pytest.mark.django_db
def test_create_and_get_booking() -> None:
    book, reader = make_book(), make_reader()
    body = {
        "book_id": book["id"],
        "reader_id": reader["id"],
        "start_date": "2026-01-01",
        "end_date": "2026-01-14",
    }
    r = post("/api/bookings", body)
    assert r.status_code == 201
    assert r.json()["status"] == "active"
    got = client.get(f"/api/bookings/{r.json()['id']}").json()
    assert got == {**body, "status": "active"}
    assert len(client.get("/api/bookings").json()) == 1


@pytest.mark.django_db
def test_booking_errors() -> None:
    book, reader = make_book(), make_reader()
    ok = {
        "book_id": book["id"],
        "reader_id": reader["id"],
        "start_date": "2026-01-01",
        "end_date": "2026-01-14",
    }
    assert post("/api/bookings", {**ok, "end_date": "2025-12-31"}).status_code == 400
    assert post("/api/bookings", {**ok, "book_id": 999999}).status_code == 404
    assert post("/api/bookings", {**ok, "reader_id": 999999}).status_code == 404
    assert client.get("/api/bookings/999999").status_code == 404


# ------------------------------------------- copies / update / delete
def booking_body(book, reader):
    return {
        "book_id": book["id"],
        "reader_id": reader["id"],
        "start_date": "2026-01-01",
        "end_date": "2026-01-14",
    }


def patch(url, body):
    return client.patch(url, json.dumps(body), content_type=JSON)


@pytest.mark.django_db
def test_booking_decrements_and_cancel_restores_copies() -> None:
    book, reader = make_book(copies_total=1), make_reader()
    r = post("/api/bookings", booking_body(book, reader))
    assert client.get(f"/api/books/{book['id']}").json()["copies_available"] == 0
    assert post("/api/bookings", booking_body(book, reader)).status_code == 409
    assert client.delete(f"/api/bookings/{r.json()['id']}").status_code == 204
    assert client.get(f"/api/books/{book['id']}").json()["copies_available"] == 1
    assert client.get(f"/api/bookings/{r.json()['id']}").json()["status"] == "cancelled"


@pytest.mark.django_db
def test_adding_same_book_adds_copies() -> None:
    first = post("/api/books", BOOK)
    again = post("/api/books", {**BOOK, "copies_total": 2})
    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json()["copies_total"] == 5
    assert again.json()["copies_available"] == 5
    assert post("/api/books", {**BOOK, "title": "Other"}).status_code == 409


@pytest.mark.django_db
def test_book_update_and_delete() -> None:
    book = make_book()
    other = make_book(isbn="222")
    url = f"/api/books/{book['id']}"
    assert patch(url, {"title": "New"}).json()["title"] == "New"
    assert patch(url, {"isbn": "222"}).status_code == 409
    assert patch("/api/books/999999", {"title": "x"}).status_code == 404
    reader = make_reader()
    post("/api/bookings", booking_body(book, reader))
    assert patch(url, {"copies_total": 5}).json()["copies_available"] == 4
    assert client.delete(url).status_code == 409  # has bookings
    assert client.delete(f"/api/books/{other['id']}").status_code == 204
    assert client.delete(f"/api/books/{other['id']}").status_code == 404


@pytest.mark.django_db
def test_reader_email_validation_update_and_delete() -> None:
    assert post("/api/readers", {**READER, "email": "not-an-email"}).status_code == 400
    assert post("/api/readers", {**READER, "email": "a@b"}).status_code == 400
    reader = make_reader(email="Jane@Example.com")
    assert reader["email"] == "jane@example.com"
    url = f"/api/readers/{reader['id']}"
    assert patch(url, {"email": "bad"}).status_code == 400
    assert patch(url, {"full_name": "Jane Q"}).json()["full_name"] == "Jane Q"
    assert client.delete(url).status_code == 204
    assert client.delete(url).status_code == 404


@pytest.mark.django_db
def test_booking_update_moves_copy_and_delete_rules() -> None:
    b1, b2, reader = (
        make_book(copies_total=1),
        make_book(isbn="222", copies_total=1),
        make_reader(),
    )
    bid = post("/api/bookings", booking_body(b1, reader)).json()["id"]
    r = patch(f"/api/bookings/{bid}", {"book_id": b2["id"], "end_date": "2026-02-01"})
    assert r.status_code == 200
    assert r.json()["book_id"] == b2["id"]
    assert client.get(f"/api/books/{b1['id']}").json()["copies_available"] == 1
    assert client.get(f"/api/books/{b2['id']}").json()["copies_available"] == 0
    assert patch(f"/api/bookings/{bid}", {"end_date": "2025-01-01"}).status_code == 400
    assert patch("/api/bookings/999999", {"end_date": "2026-02-01"}).status_code == 404
    client.delete(f"/api/bookings/{bid}")
    assert patch(f"/api/bookings/{bid}", {"end_date": "2026-03-01"}).status_code == 409
    assert client.delete(f"/api/readers/{reader['id']}").status_code == 409


def test_openapi_and_docs() -> None:
    schema = client.get("/api/openapi.json").json()
    assert "delete" in schema["paths"]["/api/bookings/{booking_id}"]
    assert "404" in schema["paths"]["/api/books/{book_id}"]["get"]["responses"]
    assert client.get("/api/docs").status_code == 200
