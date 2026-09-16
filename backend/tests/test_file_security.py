import pytest
from io import BytesIO
import zipfile
import pymupdf

from app.services.file_security_service import safe_original_name, signature_matches, validate_content_structure


@pytest.mark.parametrize(
    ("extension", "content"),
    [(".pdf", b"%PDF-1.7 data"), (".png", b"\x89PNG\r\n\x1a\nmore"), (".jpg", b"\xff\xd8\xffdata"), (".docx", b"PK\x03\x04data"), (".txt", b"safe text")],
)
def test_accepts_expected_signatures(extension: str, content: bytes) -> None:
    assert signature_matches(extension, content)


@pytest.mark.parametrize(("extension", "content"), [(".pdf", b"not pdf"), (".png", b"PNG"), (".txt", b"hello\x00binary")])
def test_rejects_mismatched_signatures(extension: str, content: bytes) -> None:
    assert not signature_matches(extension, content)


def test_windows_and_posix_traversal_names_are_reduced_to_basename() -> None:
    assert safe_original_name(r"..\..\secret.pdf") == "secret.pdf"
    assert safe_original_name("../../secret.pdf") == "secret.pdf"


def test_docx_requires_real_office_package_structure() -> None:
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    validate_content_structure(".docx", stream.getvalue(), 25 * 1024 * 1024)
    invalid = BytesIO()
    with zipfile.ZipFile(invalid, "w") as archive: archive.writestr("payload.exe", "unsafe")
    with pytest.raises(Exception): validate_content_structure(".docx", invalid.getvalue(), 25 * 1024 * 1024)


def test_pdf_structure_is_opened_and_page_limited() -> None:
    document = pymupdf.open(); document.new_page(); content = document.tobytes(); document.close()
    validate_content_structure(".pdf", content, 25 * 1024 * 1024)
    with pytest.raises(Exception): validate_content_structure(".pdf", b"%PDF-corrupt", 25 * 1024 * 1024)
