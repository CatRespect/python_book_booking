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
    r = client.post("/api/bookings/3/cancel")
    assert r.json()["status"] == "cancelled"


def test_openapi_and_docs():
    schema = client.get("/api/openapi.json").json()
    assert "/api/bookings/{booking_id}/cancel" in schema["paths"]
    assert client.get("/api/docs").status_code == 200
