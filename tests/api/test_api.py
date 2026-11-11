"""API tests. Implemented endpoints hit the real PostgreSQL test database (make db-up first)."""
import json

import pytest
from django.test import Client

client = Client()
JSON = "application/json"

BOOK = {"title": "Clean Architecture", "author": "R. Martin", "isbn": "9780134494166", "copies_total": 3}
READER = {"full_name": "Jane Doe", "email": "jane@example.com"}


def post(url, body):
    return client.post(url, json.dumps(body), content_type=JSON)


def make_book(**over):
    return post("/api/books", {**BOOK, **over}).json()


def make_reader(**over):
    return post("/api/readers", {**READER, **over}).json()


# ---------------------------------------------------------------- books
@pytest.mark.django_db
def test_create_and_get_book():
    r = post("/api/books", BOOK)
    assert r.status_code == 201
    created = r.json()
    assert created["copies_available"] == 3 and created["id"]
    assert client.get(f"/api/books/{created['id']}").json() == created
    assert client.get("/api/books").json() == [created]


@pytest.mark.django_db
def test_book_errors():
    make_book()
    assert post("/api/books", BOOK).status_code == 409            # duplicate ISBN
    assert client.get("/api/books/999999").status_code == 404
    assert post("/api/books", {**BOOK, "copies_total": 0}).status_code == 422


# -------------------------------------------------------------- readers
@pytest.mark.django_db
def test_create_and_get_reader():
    created = post("/api/readers", READER)
    assert created.status_code == 201
    rid = created.json()["id"]
    assert client.get(f"/api/readers/{rid}").json() == {"full_name": "Jane Doe"}
    assert len(client.get("/api/readers").json()) == 1


@pytest.mark.django_db
def test_reader_errors():
    make_reader()
    assert post("/api/readers", READER).status_code == 409        # duplicate email
    assert client.get("/api/readers/999999").status_code == 404


# ------------------------------------------------------------- bookings
@pytest.mark.django_db
def test_create_and_get_booking():
    book, reader = make_book(), make_reader()
    body = {"book_id": book["id"], "reader_id": reader["id"],
            "start_date": "2026-01-01", "end_date": "2026-01-14"}
    r = post("/api/bookings", body)
    assert r.status_code == 201 and r.json()["status"] == "active"
    got = client.get(f"/api/bookings/{r.json()['id']}").json()
    assert got == {**body, "status": "active"}
    assert len(client.get("/api/bookings").json()) == 1


@pytest.mark.django_db
def test_booking_errors():
    book, reader = make_book(), make_reader()
    ok = {"book_id": book["id"], "reader_id": reader["id"],
          "start_date": "2026-01-01", "end_date": "2026-01-14"}
    assert post("/api/bookings", {**ok, "end_date": "2025-12-31"}).status_code == 400
    assert post("/api/bookings", {**ok, "book_id": 999999}).status_code == 404
    assert post("/api/bookings", {**ok, "reader_id": 999999}).status_code == 404
    assert client.get("/api/bookings/999999").status_code == 404


# ---------------------------------------- stubs (no database access yet)
def test_update_and_remove_book_stub():
    r = client.patch("/api/books/4", json.dumps({"title": "New"}), content_type=JSON)
    assert r.status_code == 200 and r.json()["title"] == "New"
    assert client.delete("/api/books/4").status_code == 204


def test_update_and_remove_reader_stub():
    r = client.patch("/api/readers/4", json.dumps({"email": "x@y.com"}), content_type=JSON)
    assert r.status_code == 200 and r.json()["email"] == "x@y.com"
    assert client.delete("/api/readers/4").status_code == 204


def test_update_and_remove_booking_stub():
    body = {"book_id": 9, "reader_id": 8, "end_date": "2026-02-01"}
    r = client.patch("/api/bookings/4", json.dumps(body), content_type=JSON)
    assert r.status_code == 200
    assert (r.json()["book_id"], r.json()["reader_id"]) == (9, 8)
    assert client.delete("/api/bookings/4").status_code == 204


def test_openapi_and_docs():
    schema = client.get("/api/openapi.json").json()
    assert "delete" in schema["paths"]["/api/bookings/{booking_id}"]
    assert "404" in schema["paths"]["/api/books/{book_id}"]["get"]["responses"]
    assert client.get("/api/docs").status_code == 200
