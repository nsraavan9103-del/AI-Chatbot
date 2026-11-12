import io

import docx
import fitz
import pytest

from app.extraction import EmptyDocument, UnsupportedFileType, extract_text


def _pdf_bytes(text: str | None = None) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    if text is not None:
        page.insert_text((72, 72), text)
    return doc.tobytes()


def test_pdf_roundtrip():
    text = extract_text("a.pdf", _pdf_bytes("hello world"))
    assert "hello world" in text


def test_docx_roundtrip():
    document = docx.Document()
    document.add_paragraph("hello docx")
    buf = io.BytesIO()
    document.save(buf)
    text = extract_text("a.docx", buf.getvalue())
    assert "hello docx" in text


def test_txt_and_md_decode():
    assert extract_text("a.txt", "café".encode("utf-8")) == "café"
    assert extract_text("a.md", "café".encode("utf-8")) == "café"


def test_bom_is_stripped():
    text = extract_text("a.txt", "hi".encode("utf-8-sig"))
    assert text == "hi"


def test_unsupported_extension_raises():
    with pytest.raises(UnsupportedFileType):
        extract_text("a.csv", b"a,b")


def test_empty_pdf_raises():
    with pytest.raises(EmptyDocument):
        extract_text("scan.pdf", _pdf_bytes())
