"""Input validations. Pure functions, tested in tests/test_unit_validations.py."""
import re

# ---------------------------------------------------------------------
# User (Sprint 1 rules, kept)
# ---------------------------------------------------------------------
_RE_USER = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
_RE_EMAIL = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
_RE_PASSWORD = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$")
_RE_NAME = re.compile(r"^[A-Za-zÀ-ÿ]+(?: [A-Za-zÀ-ÿ]+)+$")


def validate_user(user: str) -> bool:
    """Letters, digits and underscore only - no spaces - 3 to 20 characters"""
    return bool(_RE_USER.match(user))


def validate_email(email: str) -> bool:
    """Pattern name@domain.com - up to 100 characters (column limit)"""
    return len(email) <= 100 and bool(_RE_EMAIL.match(email))


def validate_password(password: str) -> bool:
    """1 uppercase - 1 lowercase - 1 digit - 1 special (@$!%*?&#) - 8+ characters"""
    return bool(_RE_PASSWORD.match(password))


def validate_name(name: str) -> bool:
    """First and last name - accents allowed - no special characters - up to 100 characters"""
    return len(name) <= 100 and bool(_RE_NAME.match(name))


# ---------------------------------------------------------------------
# Free text (course name, teacher)
# ---------------------------------------------------------------------
def normalize_text(value) -> str:
    """Strips leading/trailing spaces and collapses inner spaces ('  Calculus   I ' -> 'Calculus I')."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


# ---------------------------------------------------------------------
# PDF (BR-02) - the type is decided by the CONTENT, not by what the client says
# ---------------------------------------------------------------------
PDF_MIME = "application/pdf"


def detect_mime(content: bytes) -> str:
    """Identifies a PDF by its file signature (magic bytes).

    The specification allows the '%PDF-' header within the first 1024 bytes,
    and every PDF ends with the '%%EOF' marker (possibly followed by junk).
    """
    if b"%PDF-" in content[:1024] and b"%%EOF" in content[-1024:]:
        return PDF_MIME
    return "application/octet-stream"


def validate_pdf(content: bytes, declared_mime: str | None) -> str | None:
    """Returns None if the file is a valid PDF, otherwise the error message.

    Both conditions must be true:
      1. the Content-Type declared in the multipart part is application/pdf;
      2. the actual file content is a PDF (checked on the server).
    (1) alone is not enough, because the client controls it.
    """
    declared = (declared_mime or "").split(";")[0].strip().lower()
    if declared != PDF_MIME:
        return f"declared type '{declared or 'missing'}' is not {PDF_MIME}"
    if detect_mime(content) != PDF_MIME:
        return "file content is not a valid PDF"
    return None
