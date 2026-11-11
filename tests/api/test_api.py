import json

from django.test import Client

client = Client()
JSON = "application/json"


def test_list_books():
    r = client.get("/api/books")
    assert r.status_code == 200
    assert r.json()[0]["title"]


def test_get_book():
    assert client.get("/api/books/7").json()["id"] == 7


def test_create_book():
    body = {"title": "T", "author": "A", "isbn": "1", "copies_total": 2}
    r = client.post("/api/books", json.dumps(body), content_type=JSON)
    assert r.status_code == 201
    assert r.json()["copies_available"] == 2


def test_create_book_validation():
    body = {"title": "T", "author": "A", "isbn": "1", "copies_total": 0}
    assert client.post("/api/books", json.dumps(body), content_type=JSON).status_code == 422


def test_readers():
    assert client.get("/api/readers").status_code == 200
    body = {"full_name": "J D", "email": "j@d.com"}
    assert client.post("/api/readers", json.dumps(body), content_type=JSON).status_code == 201


def test_bookings():
    assert client.get("/api/bookings").status_code == 200
    body = {"book_id": 1, "reader_id": 1, "start_date": "2026-01-01", "end_date": "2026-01-14"}
    assert client.post("/api/bookings", json.dumps(body), content_type=JSON).status_code == 201


def test_openapi_and_docs():
    schema = client.get("/api/openapi.json").json()
    assert "delete" in schema["paths"]["/api/bookings/{booking_id}"]
    assert client.get("/api/docs").status_code == 200


def test_update_and_remove_book():
    r = client.patch("/api/books/4", json.dumps({"title": "New"}), content_type=JSON)
    assert r.status_code == 200
    assert r.json()["title"] == "New" and r.json()["author"] == "Robert C. Martin"
    assert client.delete("/api/books/4").status_code == 204


def test_update_and_remove_booking():
    body = {"book_id": 9, "reader_id": 8, "end_date": "2026-02-01"}
    r = client.patch("/api/bookings/4", json.dumps(body), content_type=JSON)
    assert r.status_code == 200
    assert (r.json()["book_id"], r.json()["reader_id"], r.json()["end_date"]) == (9, 8, "2026-02-01")
    assert client.delete("/api/bookings/4").status_code == 204


def test_update_and_remove_reader():
    r = client.patch("/api/readers/4", json.dumps({"email": "x@y.com"}), content_type=JSON)
    assert r.status_code == 200
    assert r.json()["email"] == "x@y.com" and r.json()["full_name"] == "Jane Doe"
    assert client.delete("/api/readers/4").status_code == 204


def test_get_reader_returns_only_name():
    r = client.get("/api/readers/3")
    assert r.status_code == 200
    assert r.json() == {"full_name": "Jane Doe"}


def test_get_booking_fields():
    r = client.get("/api/bookings/3")
    assert r.status_code == 200
    assert set(r.json()) == {"book_id", "reader_id", "start_date", "end_date", "status"}
