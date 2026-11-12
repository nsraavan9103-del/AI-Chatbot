import io
import re
from pathlib import Path

import docx
import fitz

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class UnsupportedFileType(ValueError):
    pass


class EmptyDocument(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileType(f"Unsupported file type: {suffix or '(none)'}")

    if suffix == ".pdf":
        with fitz.open(stream=data, filetype="pdf") as doc:
            text = "\n".join(page.get_text() for page in doc)
    elif suffix == ".docx":
        document = docx.Document(io.BytesIO(data))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    else:
        text = data.decode("utf-8-sig", errors="replace")

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise EmptyDocument("No extractable text")
    return text
