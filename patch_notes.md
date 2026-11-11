# Patch notes v0.3.0: availability, email validation, full update/delete

## 1. Summary

| Requested | Result |
|---|---|
| `copies_available` decreases on booking | Done. Atomic, row-locked, 409 when no copy is left |
| `copies_available` increases when a book with same ISBN + title + author is added | Done. `POST /books` adds copies to the existing book (200 instead of 201) |
| Email regex check | Done. In the domain layer, returns 400; emails are also trimmed and lower-cased |
| Remaining update + delete | Done for books, readers, bookings (no stubs left) |
| Review of the whole code | Section 6 |

Verification: **65 tests pass** (was 18) on PostgreSQL 16, plus a manual concurrency run:
10 simultaneous bookings of the last copy gave exactly one 201 and nine 409, final
`copies_available = 0`. The sandbox ran Python 3.12 (your project asks for 3.14), so run
`make test` once on your machine.

## 2. Behaviour rules (the contract)

**Books**
- `POST /books`, ISBN unknown: new book, all copies available -> **201**.
- `POST /books`, same ISBN **and** same title and author (case and extra spaces ignored): the
  `copies_total` you send is **added** to both `copies_total` and `copies_available` -> **200**.
- `POST /books`, same ISBN but different title/author: **409** (probably a typo, not "more copies").
- `PATCH /books/{id}`: `copies_total` means the **new total stock**. Copies on loan stay on loan, so
  `copies_available = new_total - on_loan`. Lowering the total below the loaned count -> **409**.
  A taken ISBN -> **409**.
- `DELETE /books/{id}`: **409** if any booking (even cancelled) references it, else 204.

**Readers**
- Email is trimmed, lower-cased, and must match the pattern below, else **400**. Applies to POST and PATCH.
- `DELETE /readers/{id}`: **409** if the reader has any booking.

**Bookings**
- `POST`: takes one copy; **409** when `copies_available` is 0. Nothing is stored on failure.
- `PATCH`: only **active** bookings (409 otherwise). Dates are re-validated against the merged values (400).
  Changing `book_id` returns the old copy and takes one from the new book (409 if none).
- `DELETE`: soft delete. Status becomes `cancelled` and the copy is returned. Repeating it is a
  no-op (204). Deleting a `returned` booking -> 409.
- In every PATCH, `null` is treated as "not sent".

Email pattern (`domain/validators.py`): `local@label.label.tld`. Local part has letters, digits and
common specials, with dots only *between* characters. Domain labels are alphanumeric with inner
hyphens, there must be at least one dot, and the TLD is 2+ letters. Max 254 chars total and 64
for the local part. It rejects `a@.com`, `a@b.`, `a@b..c`, `a b@c.de`, and `a@b`. It is
deliberately not full RFC 5322, and non-ASCII domains must be given as punycode.

## 3. What changed, by layer, and why

### Domain (still no Django)
- **`validators.py` (new)**: the email regex, `normalize_email`, `normalize_text`. *Why here:* an
  email format is a business rule; it must hold no matter which interface (API, CLI) is used.
  Labels are written unambiguously, so the regex runs in linear time (tested against hostile input).
- **`entities.py`**: `Book` gained behaviour: `with_copy_taken()`, `with_copy_returned()`,
  `with_copies_added()`, `with_total_copies()`, `is_same_edition()`. They return a changed copy
  instead of mutating. *Why:* the copy-count rules are the heart of the domain, so they live on
  the entity, not scattered across use cases or the ORM. `NewBook` also checks
  `available <= total`.
- **`exceptions.py`**: new `NoCopiesAvailable`, `CopiesInUse`, `IsbnBelongsToAnotherBook`,
  `BookHasBookings`, `ReaderHasBookings`, `BookingNotActive` (all 409) and `InvalidEmail` (400).
  They reuse your existing category -> HTTP mapping, so `api.py` needed no new handlers.
- **`repositories.py` (ports)**: added `get_by_isbn`, `get_for_update`, `save`, `delete`,
  `exists_for_book/reader`, and a new **`UnitOfWork`** port (`atomic()`). *Why:* your v0.2.0 notes
  listed a Unit of Work as the next step. Booking now changes two tables (book + booking), and
  that must be all-or-nothing without the use case knowing about Django transactions.

### Application
- **`use_cases.py`**: all stubs replaced. Multi-row operations run inside `uow.atomic()` and lock
  the rows they read with `get_for_update` (`SELECT ... FOR UPDATE`). *Why:* "read available, then
  write available-1" is a classic race; without the lock two requests both see 1 copy.
  When two books are locked at once (moving a booking) they are locked in ascending id order to
  avoid deadlocks. `create_book` also survives the race where another request inserts the same ISBN
  between the lookup and the insert.
- **Signature changes** (your call sites in `api.py` are updated): `create_book(books, uow, data)`
  now returns `CreateBookOutput(book, created)`; `create_booking(..., uow, data)`; `update_*` and
  `remove_*` now take repositories first like the rest.
- **`dto.py`**: titles/authors/ISBN/name are trimmed, non-empty and capped to the column length.
  *Why:* a 300-char title used to pass validation and crash PostgreSQL with a 500 (now 422).

### Infrastructure
- **`repositories.py`**: implementations of the new ports. `DjangoUnitOfWork` wraps
  `transaction.atomic()`. `delete` maps Django's `ProtectedError` to `BookHasBookings` /
  `ReaderHasBookings` as a last safety net behind the use-case check.
- **Bug fix:** previously *any* `IntegrityError` was reported as "ISBN/email already exists".
  Now only PostgreSQL's unique-violation code (23505) is, so CHECK/FK failures are not disguised.
- **No migration needed**: the schema already had the `available <= total` check and the ISBN unique.

### Presentation / config
- `api.py`: endpoints call the real use cases; each declares its 400/404/409 responses so Swagger is
  accurate; version 0.3.0. `container.py`: added `unit_of_work()`. `swagger.json` regenerated.

## 4. Key decisions, and alternatives I rejected

1. **Row locks (`select_for_update`) instead of `UPDATE ... WHERE copies_available > 0`.** The
   single conditional UPDATE is also race-free, but it hides the rule in SQL. With the lock the rule
   stays in the `Book` entity and is unit-testable without a database.
2. **Booking cancellation returns the copy**, although you didn't ask. Without it, DELETE would
   leak copies forever and availability would drift from reality.
3. **`create_book` merges instead of 409** only when ISBN *and* title *and* author match. If only
   the ISBN matches I return 409, because silently merging two different books would corrupt data.
4. **Emails are lower-cased.** This fixes the "uniqueness is case-sensitive" limitation from
   v0.2.0. Rows created before this patch are not migrated; lower-case them once if you have any.
5. **Cancelled bookings still block deleting a book/reader.** That matches the existing
   `on_delete=PROTECT` and keeps history. The alternative (allow deletion when only cancelled bookings
   exist) would need `SET_NULL`/archiving, which is a bigger design choice.
6. **Fake unit of work really rolls back** (snapshots the in-memory repos), so unit tests can prove
   "nothing is stored when a rule fails".

## 5. Tests

- `tests/unit/test_validators.py`, `test_entities.py` (new): email cases, copy arithmetic.
- `tests/unit/test_use_cases.py`: existing tests adapted to the new signatures; new availability,
  merge, cancel, move and update/delete tests.
- `tests/api/test_api.py`: the six "stub" tests were replaced by real end-to-end tests.
- Two old assertions changed on purpose: posting the same ISBN with the same title/author used to
  be 409 and is now "add copies"; the 409 case now uses a different title.
- Not covered by automated tests: concurrency (checked manually, see Summary).

## 6. Review of the whole code

**Architecture (good):** dependencies point inward (`presentation -> application -> domain <-
infrastructure`), ORM models are separate from entities, the composition root is one file, and
use cases are testable with fakes. Two honest trade-offs to know about:
- The domain imports **pydantic**. Pragmatic and common, but strictly the domain is not
  framework-free. Fine for learning; plain dataclasses would be the purist version.
- `api.py` returns domain entities (`Book`, `Booking`, `Reader`) directly as response schemas, so
  the API contract and the domain model are coupled. Dedicated response DTOs would decouple them.

**Things I found but did NOT change (your files, your call):**
1. **CI will fail:** there is no PostgreSQL service in `.github/workflows/base.yml`, `pytest-django`
   is not in the dev dependencies / `poetry.lock` (the tests use `django_db`), and CI never sets up
   Python 3.14 although `requires-python >= 3.14`. Ruff targets `py312` in `pyproject.toml` but
   `py311` in CI.
2. **`docker-compose.yml`** mounts `./docker/postgres/init.sql`, which doesn't exist (Docker will
   create a directory there and Postgres init can fail or misbehave). Create the file or remove the line.
3. **`pyproject.toml`**: project name is still `hw2`, and `packages = [{include = "hw2"...}]` points
   to a package that doesn't exist. `Dockerfile` is empty. `makefile` `.PHONY` lists `check` (no such
   target) and misses most targets. `Readme.md` still has the "should be a description here" placeholder.
4. **Dead files:** `presentation/serializers.py`, `views.py`, `urls.py` (empty), `.gitkeep`, and
   `tests/test_example.py`. Safe to delete.
5. **Linters:** I ran ruff (pyflakes + import order) and black on the changed code, but **not**
   your full `select = ["ALL"]` ruff config or mypy (no `django-stubs`), so expect new findings
   there. Run `make lint` and `make format`.
6. `ALLOWED_HOSTS = ["*"]` and the default `SECRET_KEY` are fine for development only.

## 7. Known limitations / next steps

- There is **no "return a book" operation**: status `returned` exists but nothing sets it. A
  `POST /bookings/{id}/return` (returns the copy, sets `returned`) is the natural next feature.
- **Overlapping bookings are not checked**; availability is a simple counter, not date-based.
- ISBNs are matched exactly (`978-0-13...` and `9780134...` are different). Normalising hyphens is easy to add.
- No pagination, no authentication (unchanged).
- Suggested: `import-linter` in CI to enforce the layer rules automatically.
