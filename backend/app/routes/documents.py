import sqlite3

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile

from app.chunking import chunk_text
from app.deps import get_db
from app.embeddings import encode_vector
from app.extraction import EmptyDocument, UnsupportedFileType, extract_text
from app.schemas import DocumentOut

router = APIRouter()


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
    return [DocumentOut(**dict(row)) for row in rows]


@router.post("/documents", status_code=201)
def upload_documents(
    request: Request,
    files: list[UploadFile] = File(...),
    conn: sqlite3.Connection = Depends(get_db),
):
    settings = request.app.state.settings
    embedder = request.app.state.embedder
    documents: list[DocumentOut] = []
    errors: list[dict[str, str]] = []

    for upload in files:
        filename = upload.filename or "upload"
        try:
            data = upload.file.read()
            if len(data) > settings.max_upload_mb * 1024 * 1024:
                raise ValueError(f"File larger than {settings.max_upload_mb} MB")
            text = extract_text(filename, data)
            chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
            if len(chunks) > settings.max_chunks_per_document:
                raise ValueError(
                    f"Document exceeds {settings.max_chunks_per_document} chunks"
                )
            vectors = embedder.embed_documents(chunks)
            cursor = conn.execute(
                "INSERT INTO documents"
                " (filename, content_type, size_bytes, char_count, chunk_count)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    filename,
                    upload.content_type or "application/octet-stream",
                    len(data),
                    len(text),
                    len(chunks),
                ),
            )
            document_id = cursor.lastrowid
            conn.executemany(
                "INSERT INTO chunks (document_id, idx, text, embedding)"
                " VALUES (?, ?, ?, ?)",
                [
                    (document_id, idx, chunk, encode_vector(vec))
                    for idx, (chunk, vec) in enumerate(zip(chunks, vectors))
                ],
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
            documents.append(DocumentOut(**dict(row)))
        except (UnsupportedFileType, EmptyDocument, ValueError) as exc:
            conn.rollback()
            errors.append({"filename": filename, "error": str(exc)})

    return {"documents": documents, "errors": errors}


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(status_code=204)
