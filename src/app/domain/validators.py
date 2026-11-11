"""Pure validation / normalisation helpers. No framework imports."""

import re

# A pragmatic email check (not full RFC 5322, on purpose).
#   local part : letters, digits and the usual specials, dots only BETWEEN characters
#   domain     : dot-separated labels (letters, digits, inner hyphens), at least one dot
#   TLD        : letters only, 2+ characters
# It is stricter than the naive "*@*.*": it rejects malformed local and domain parts.
# Labels are written so that there is only one way to match them. This keeps the
# regex linear-time and avoids catastrophic backtracking on hostile input.
_LOCAL = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
_LABEL = r"[A-Za-z0-9]+(?:-+[A-Za-z0-9]+)*"
EMAIL_RE = re.compile(rf"{_LOCAL}@(?:{_LABEL}\.)+[A-Za-z]{{2,}}")

MAX_EMAIL_LENGTH = 254  # same limit as Django's EmailField
MAX_LOCAL_LENGTH = 64


def normalize_email(email: str) -> str:
    """Trim and lower-case, so 'Jane@X.com' and 'jane@x.com' are the same reader."""
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    """Return True if the (already normalised) address looks like local@domain.tld."""
    if len(email) > MAX_EMAIL_LENGTH:
        return False
    local, _, _ = email.partition("@")
    if len(local) > MAX_LOCAL_LENGTH:
        return False
    return EMAIL_RE.fullmatch(email) is not None


def normalize_text(value: str) -> str:
    """Collapse whitespace and ignore case, for comparing titles / authors."""
    return " ".join(value.split()).casefold()
