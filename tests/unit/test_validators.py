import pytest

from app.domain.validators import is_valid_email, normalize_email, normalize_text


@pytest.mark.parametrize(
    "email",
    [
        "jane@example.com",
        "a@b.co",
        "first.last@sub.example.org",
        "user+tag@example.com",
        "o'brien@example.ie",
        "x_y-z@my-host.example.io",
        "1234@5678.com",
    ],
)
def test_valid_emails(email) -> None:
    assert is_valid_email(email)


@pytest.mark.parametrize(
    "email",
    [
        "",
        "plainaddress",
        "@example.com",  # empty local part
        "jane@",  # empty domain
        "jane@example",  # no dot in the domain
        "jane@.com",  # empty label
        "jane@example.",  # empty TLD
        "jane@example..com",  # empty label in the middle
        "jane@@example.com",  # two @
        "ja ne@example.com",  # whitespace
        "jane@exa mple.com",
        ".jane@example.com",  # leading dot
        "jane.@example.com",  # trailing dot
        "ja..ne@example.com",  # consecutive dots
        "jane@-example.com",  # label starts with a hyphen
        "jane@example-.com",  # label ends with a hyphen
        "jane@example.c",  # one-letter TLD
        "jane@example.c0m",  # digits in TLD
        "jane@exämple.com",  # non-ASCII (needs punycode)
        "a" * 65 + "@example.com",  # local part too long
        "a@" + "b" * 250 + ".com",  # total length too long
    ],
)
def test_invalid_emails(email) -> None:
    assert not is_valid_email(email)


def test_normalize_email_trims_and_lowercases() -> None:
    assert normalize_email("  Jane@Example.COM ") == "jane@example.com"


def test_regex_is_not_catastrophic_on_hostile_input() -> None:
    # A backtracking-prone regex would hang here; ours answers immediately.
    assert not is_valid_email("a" * 60 + "@" + ("a-" * 100) + "!")


def test_normalize_text_ignores_case_and_spacing() -> None:
    assert normalize_text("  Clean   Architecture ") == normalize_text(
        "clean architecture"
    )
