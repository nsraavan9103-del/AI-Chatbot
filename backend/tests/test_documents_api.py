import sqlite3

from fastapi.testclient import TestClient

from app.main import create_app


def _upload(client, name, data, content_type="text/plain"):
    return client.post("/api/documents", files={"files": (name, data, content_type)})


def test_health_reports_llm_not_configured(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "llm_configured": False}


def test_upload_txt_returns_document_with_chunk_count(client):
    response = _upload(client, "a.txt", b"hello world")
    assert response.status_code == 201
    body = response.json()
    assert body["errors"] == []
    assert len(body["documents"]) == 1
    assert body["documents"][0]["filename"] == "a.txt"
    assert body["documents"][0]["chunk_count"] >= 1


def test_upload_multiple_files_partial_failure(client):
    response = client.post(
        "/api/documents",
        files=[
            ("files", ("good.txt", b"hello", "text/plain")),
            ("files", ("bad.csv", b"a,b", "text/csv")),
        ],
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["documents"]) == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["filename"] == "bad.csv"


def test_corrupt_pdf_is_an_error_entry_not_a_500(client):
    response = client.post(
        "/api/documents",
        files={"files": ("broken.pdf", b"not a pdf", "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["documents"] == []
    assert len(body["errors"]) == 1
    assert body["errors"][0]["filename"] == "broken.pdf"


def test_upload_without_files_is_422(client):
    assert client.post("/api/documents").status_code == 422


def test_upload_oversized_file_is_rejected(client, settings):
    settings.max_upload_mb = 0
    response = _upload(client, "big.txt", b"hello")
    assert response.status_code == 201
    body = response.json()
    assert body["documents"] == []
    assert len(body["errors"]) == 1


def test_list_documents_newest_first(client):
    _upload(client, "first.txt", b"one")
    _upload(client, "second.txt", b"two")
    response = client.get("/api/documents")
    assert response.status_code == 200
    assert [doc["filename"] for doc in response.json()] == ["second.txt", "first.txt"]


def test_delete_document_removes_chunks(client, settings):
    document_id = _upload(client, "a.txt", b"hello world").json()["documents"][0]["id"]
    assert client.delete(f"/api/documents/{document_id}").status_code == 204
    assert client.get("/api/documents").json() == []
    with sqlite3.connect(settings.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 0


def test_delete_missing_document_is_404(client):
    assert client.delete("/api/documents/999").status_code == 404


def test_data_survives_app_restart(settings, fake_embedder, fake_llm_stream):
    first = TestClient(create_app(settings, embedder=fake_embedder, llm_stream=fake_llm_stream))
    _upload(first, "a.txt", b"hello world")

    second = TestClient(create_app(settings, embedder=fake_embedder, llm_stream=fake_llm_stream))
    documents = second.get("/api/documents").json()
    assert [doc["filename"] for doc in documents] == ["a.txt"]
