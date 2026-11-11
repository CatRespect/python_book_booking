import pytest
from pydantic import ValidationError

from app.domain.entities import Book
from app.domain.exceptions import CopiesInUse, NoCopiesAvailable


def _book(total=3, available=3):
    return Book(
        id=1,
        title="T",
        author="A",
        isbn="1",
        copies_total=total,
        copies_available=available,
    )


def test_take_and_return_copy():
    book = _book().with_copy_taken()
    assert book.copies_available == 2
    assert book.with_copy_returned().copies_available == 3


def test_take_copy_when_none_left():
    with pytest.raises(NoCopiesAvailable):
        _book(available=0).with_copy_taken()


def test_return_never_exceeds_total():
    assert _book().with_copy_returned().copies_available == 3


def test_add_copies_grows_total_and_available():
    book = _book(total=3, available=1).with_copies_added(2)
    assert (book.copies_total, book.copies_available) == (5, 3)


def test_set_total_keeps_loans():
    book = _book(total=3, available=1).with_total_copies(5)  # 2 on loan
    assert (book.copies_total, book.copies_available) == (5, 3)
    assert _book(total=3, available=1).with_total_copies(2).copies_available == 0


def test_set_total_below_loans_rejected():
    with pytest.raises(CopiesInUse):
        _book(total=3, available=0).with_total_copies(2)  # 3 on loan


def test_available_cannot_exceed_total():
    with pytest.raises(ValidationError):
        _book(total=1, available=2)


def test_same_edition_ignores_case_and_spaces():
    assert _book().is_same_edition(" t ", "a")
    assert not _book().is_same_edition("T", "Other")
