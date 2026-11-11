"""Unit tests for the domain entities."""

import pytest
from pydantic import ValidationError

from app.domain.entities import Book
from app.domain.exceptions import CopiesInUseError, NoCopiesAvailableError

TWO_COPIES = 2
THREE_COPIES = 3


def _book(total: int = 3, available: int = 3) -> Book:
    """Build a domain book for entity tests."""
    return Book(
        id=1,
        title="T",
        author="A",
        isbn="1",
        copies_total=total,
        copies_available=available,
    )


def test_take_and_return_copy() -> None:
    """Test take and return copy."""
    book = _book().with_copy_taken()
    assert book.copies_available == TWO_COPIES
    assert book.with_copy_returned().copies_available == THREE_COPIES


def test_take_copy_when_none_left() -> None:
    """Test take copy when none left."""
    with pytest.raises(NoCopiesAvailableError):
        _book(available=0).with_copy_taken()


def test_return_never_exceeds_total() -> None:
    """Test return never exceeds total."""
    assert _book().with_copy_returned().copies_available == THREE_COPIES


def test_add_copies_grows_total_and_available() -> None:
    """Test add copies grows total and available."""
    book = _book(total=3, available=1).with_copies_added(2)
    assert (book.copies_total, book.copies_available) == (5, 3)


def test_set_total_keeps_loans() -> None:
    """Test set total keeps loans."""
    book = _book(total=3, available=1).with_total_copies(5)  # 2 on loan
    assert (book.copies_total, book.copies_available) == (5, 3)
    assert _book(total=3, available=1).with_total_copies(2).copies_available == 0


def test_set_total_below_loans_rejected() -> None:
    """Test set total below loans rejected."""
    with pytest.raises(CopiesInUseError):
        _book(total=3, available=0).with_total_copies(2)  # 3 on loan


def test_available_cannot_exceed_total() -> None:
    """Test available cannot exceed total."""
    with pytest.raises(ValidationError):
        _book(total=1, available=2)


def test_same_edition_ignores_case_and_spaces() -> None:
    """Test same edition ignores case and spaces."""
    assert _book().is_same_edition(" t ", "a")
    assert not _book().is_same_edition("T", "Other")
