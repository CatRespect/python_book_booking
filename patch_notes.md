# Patch notes: database connection + real GET / CREATE (v0.2.0)

## 1. Summary

The API now stores data in PostgreSQL. **List, get-by-id and create** work for all three
resources (books, readers, bookings). **PATCH and DELETE are still stubs** returning sample
data, exactly as before.

| Resource | `GET` list | `GET /{id}` | `POST` | `PATCH /{id}` | `DELETE /{id}` |
|---|---|---|---|---|---|
| Books    | real | real (full book) | real | stub | stub |
| Readers  | real | real (`full_name` only) | real | stub | stub |
| Bookings | real | real (no `id`) | real | stub | stub |

Verified: 17 automated tests pass (7 unit tests with no database, 10 API tests against a real
PostgreSQL 16), plus a manual run against a live server. The sandbox used a locally installed
PostgreSQL 16, **not** your Docker container, so run `make db-up` and the tests once on your machine.

## 2. What changed, by layer

### Domain (`src/app/domain/`) - still pure Python
- **`entities.py`**: each entity is now split in two: `NewBook` / `NewReader` / `NewBooking`
  (data *before* it is stored, no `id`) and `Book` / `Reader` / `Booking` (extend the New* class
  with `id`).
  *Why:* the database assigns ids. Without this split, creating an entity would need a fake id or
  `id: int | None`, which would leak "maybe no id" into every API response schema.
- **`exceptions.py`** (new): `BookNotFound`, `ReaderNotFound`, `BookingNotFound`,
  `BookAlreadyExists`, `ReaderAlreadyExists`, `InvalidBookingPeriod`, grouped under three
  categories: `NotFoundError`, `ConflictError`, `InvalidInputError`.
  *Why:* business failures are expressed in business terms; the domain knows nothing about HTTP.
- **`repositories.py`**: ports updated: `add()` takes a `New*` object and returns the stored
  entity; `ReaderRepository.get()` added (needed to validate bookings).

### Application (`src/app/application/use_cases.py`)
- Implemented `list_*`, `get_*`, `create_*` for the three resources. Each takes the repositories
  it needs as its **first arguments** (e.g. `get_book(books, book_id)`).
  *Why:* plain functions with injected ports keep the style of the previous prototype, need no
  classes, and can be tested with in-memory fakes.
- `create_book` sets `copies_available = copies_total` (a new title starts fully available).
- `create_booking` applies three rules in order: `end_date >= start_date`, the book exists, the
  reader exists.
- `update_*` / `remove_*` remain stubs in a clearly marked section at the bottom of the file.

### Infrastructure (`src/app/infrastructure/`) - all Django ORM lives here
- **`models.py`**: `BookModel`, `ReaderModel`, `BookingModel` (tables `books`, `readers`, `bookings`).
- **`repositories.py`**: `DjangoBookRepository`, `DjangoReaderRepository`,
  `DjangoBookingRepository` implement the domain ports. ORM rows become domain entities via
  `Entity.model_validate(row, from_attributes=True)`, so no hand-written mapper layer is needed.
- **`apps.py`** + **`migrations/0001_initial.py`**: registers the models as the Django app labelled
  `booking` and creates the schema.

### Presentation (`src/app/presentation/api.py`)
- Endpoints call use cases and pass repositories from the container.
- **Domain error -> HTTP mapping**, done once with exception handlers:
  `NotFoundError` -> **404**, `ConflictError` -> **409**, `InvalidInputError` -> **400**, all with
  body `{"detail": "..."}`.
- Error responses are declared per endpoint, so they appear in Swagger (`ErrorResponse` schema).
- API version bumped to 0.2.0; stub endpoints are labelled "(stub)" in their summaries.

### Composition root (`src/config/container.py`, new)
The only module that knows both the abstract ports and the concrete Django classes. To swap a
storage implementation (or use fakes), this is the one file to change.

### Settings (`src/config/settings.py`)
- Registered `app.infrastructure.apps.InfrastructureConfig` in `INSTALLED_APPS`.
- Added `CONN_MAX_AGE=60` and `CONN_HEALTH_CHECKS=True` (see decision 6 below).

## 3. Database schema

| Table | Columns | Constraints |
|---|---|---|
| `books` | id, title, author, isbn, copies_total, copies_available | `isbn` UNIQUE; `copies_available <= copies_total`; both counts >= 0 |
| `readers` | id, full_name, email | `email` UNIQUE |
| `bookings` | id, book_id, reader_id, start_date, end_date, status | FKs to books/readers (`PROTECT`); `end_date >= start_date`; status in active/returned/cancelled |

## 4. Key decisions and why

1. **ORM models are separate from domain entities.** Django models describe storage; entities
   describe the business. Keeping them apart means the domain imports no Django, and the
   database can change without touching business rules. The cost: a conversion at the repository
   boundary (one line, see above).
2. **Repository ports + in-memory fakes.** Use cases only see abstract repositories, so
   `tests/unit/` exercises all business rules in milliseconds with no database.
3. **Rules in both the use case and the database.** The use case gives friendly errors (404/400/409).
   The DB constraints (unique, check, foreign keys) are the safety net against bugs and races.
4. **Duplicates detected via the unique constraint, not a "check then insert".** Two simultaneous
   requests could both pass a pre-check; the constraint cannot be raced. The repository catches
   the resulting `IntegrityError` inside `transaction.atomic()` (a savepoint, so the connection
   stays usable) and raises `BookAlreadyExists` / `ReaderAlreadyExists`.
5. **Booking creation checks that the book and the reader exist** and returns a clear 404, instead
   of letting a foreign-key violation surface as a 500.
6. **Persistent connections.** `CONN_MAX_AGE=60` avoids opening a new PostgreSQL connection per
   request; `CONN_HEALTH_CHECKS` discards a connection that died (e.g. after a DB restart) instead
   of failing the next request.
7. **Status codes:** business-rule violations on input (e.g. dates reversed) use **400** with
   `{"detail": str}`. Schema validation errors keep Ninja's own **422** format (`{"detail": [...]}`).
   The two shapes differ, so clients should handle both.
8. **Foreign keys use `PROTECT`.** A book or reader with bookings cannot be deleted; this matters
   when DELETE is implemented.

## 5. How to run

```bash
cp .env.example .env
make db-up         # PostgreSQL in Docker
make migrate       # create the tables (first run, and after every pull with new migrations)
make run           # http://localhost:8000/api/docs
make test
make swagger       # refresh swagger.json in the project root
```

Dependencies to add if you haven't: `poetry add django django-ninja "psycopg[binary]"` and
`poetry add --group dev pytest pytest-django`. Django **5.1 or newer** is required (`CheckConstraint(condition=...)`).

New root file `pytest.ini` points pytest at the Django settings and adds `src` to the path (it
replaces the old `tests/conftest.py`). If your `pyproject.toml` already has pytest settings,
pytest.ini takes precedence; merge as you prefer.

API tests create a separate `test_<dbname>` database, so the database user needs the CREATEDB
privilege. The Docker `POSTGRES_USER` is a superuser, so this works out of the box there.

## 6. Tests

- `tests/unit/test_use_cases.py` (7 tests, **no database**): copies default, duplicate ISBN/email,
  not-found errors, booking rules (bad period, missing book, missing reader).
- `tests/api/test_api.py` (10 tests): create/get/list round trips on real PostgreSQL, 404/409/400/422
  paths, stub endpoints, OpenAPI contents.
- Not covered by automated tests: behaviour under concurrent requests.

## 7. Known limitations (intentionally out of scope for this patch)

- **No availability logic.** Creating a booking does not decrement `copies_available`, and nothing
  stops more bookings than copies or overlapping bookings of the same copy.
- **PATCH / DELETE are stubs**: they do not touch the database. `GET /bookings/{id}` therefore
  reads real data while `PATCH /bookings/{id}` still returns sample data.
- **No pagination or filtering** on list endpoints; they return every row (ordered by id).
- **No authentication or authorisation.** `ALLOWED_HOSTS = ["*"]` and the default secret key are
  development-only settings.
- **Email format is not validated** (stored as a plain string in the API layer, `EmailField` in the
  ORM only validates in forms). Email uniqueness is case-sensitive.
- **Booking creation is not wrapped in one transaction** with its checks; the FK constraints
  catch the race where a book/reader is deleted in between (would surface as a 500).
- The migration was generated and applied on PostgreSQL 16 / Django 6.1 in the development sandbox.

## 8. Suggested next steps

1. Implement update/remove (including `remove_booking` as a soft delete -> `status=cancelled`).
2. Booking rules: availability, overlap detection, decrement/increment `copies_available` inside one
   transaction (add a Unit of Work port), plus an index on `(book_id, start_date, end_date)`.
3. Pagination on list endpoints.
4. Enforce layer boundaries in CI with `import-linter`.
