"""Unit: validations.py. Does not use the database."""
import pytest

from validations import (
    detect_mime,
    normalize_text,
    validate_email,
    validate_name,
    validate_password,
    validate_pdf,
    validate_user,
)

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


# ---------------- BR-02: PDF detection by content ----------------
@pytest.mark.req("BR-02")
@pytest.mark.parametrize(
    "content,expected",
    [
        (MINIMAL_PDF, "application/pdf"),
        (b"\x00" * 10 + MINIMAL_PDF, "application/pdf"),  # header may not be at byte 0
        (MINIMAL_PDF + b"\n" * 50, "application/pdf"),  # junk after %%EOF
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "application/octet-stream"),
        (b"<html><body>%PDF-</body></html>", "application/octet-stream"),  # no %%EOF
        (b"%PDF-1.7 truncated", "application/octet-stream"),
        (b"", "application/octet-stream"),
    ],
    ids=["pdf", "pdf-with-preamble", "pdf-with-trailing-junk", "png", "disguised-html", "truncated-pdf", "empty"],
)
def test_detect_mime(content, expected):
    assert detect_mime(content) == expected


@pytest.mark.req("BR-02")
def test_validate_pdf_accepts_pdf_with_correct_type():
    assert validate_pdf(MINIMAL_PDF, "application/pdf") is None
    assert validate_pdf(MINIMAL_PDF, "Application/PDF; charset=binary") is None


@pytest.mark.req("BR-02")
@pytest.mark.parametrize("declared", [None, "", "image/png", "application/octet-stream"])
def test_validate_pdf_rejects_wrong_declared_type_even_with_pdf_content(declared):
    assert validate_pdf(MINIMAL_PDF, declared) is not None


@pytest.mark.req("BR-02")
def test_validate_pdf_rejects_fake_content_even_if_declared_as_pdf():
    """The core of BR-02: do not trust the type the client declares."""
    assert validate_pdf(b"this is a renamed .txt", "application/pdf") is not None


# ---------------- BR-01 support: text normalization ----------------
@pytest.mark.req("BR-01")
@pytest.mark.parametrize(
    "value,result",
    [("  Cálculo   I ", "Cálculo I"), ("Prof.\tAna", "Prof. Ana"), ("", ""), (None, ""), (123, "")],
)
def test_normalize_text(value, result):
    assert normalize_text(value) == result


# ---------------- FR-08: registration rules (Sprint 1) ----------------
@pytest.mark.req("FR-08")
@pytest.mark.parametrize("value,ok", [("joao_1", True), ("ab", False), ("a" * 21, False), ("joão", False), ("jo ao", False)])
def test_validate_user(value, ok):
    assert validate_user(value) is ok


@pytest.mark.req("FR-08")
@pytest.mark.parametrize("value,ok", [("a.b+c@uni.edu.br", True), ("noatsign.com", False), ("a@b", False), ("x" * 95 + "@a.com", False)])
def test_validate_email(value, ok):
    assert validate_email(value) is ok


@pytest.mark.req("FR-08")
@pytest.mark.parametrize("value,ok", [("Secret@123", True), ("secret@123", False), ("Secret1234", False), ("Se@1", False)])
def test_validate_password(value, ok):
    assert validate_password(value) is ok


@pytest.mark.req("FR-08")
@pytest.mark.parametrize("value,ok", [("João Silva", True), ("Maria", False), ("Ana_Paula Souza", False), ("Ana  Souza", False)])
def test_validate_name(value, ok):
    assert validate_name(value) is ok
