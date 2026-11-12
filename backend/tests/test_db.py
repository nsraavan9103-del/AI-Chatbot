import sqlite3

from app.config import Settings
from app.db import connect, init_db

TABLES = {"documents", "chunks", "chats", "messages", "message_sources"}


def test_init_db_creates_all_tables(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert TABLES <= names


def test_init_db_is_idempotent(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    assert count == 0


def test_foreign_keys_cascade(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO documents (filename, content_type, size_bytes, char_count, chunk_count)"
            " VALUES ('a.txt', 'text/plain', 5, 5, 1)"
        )
        doc_id = cur.lastrowid
        conn.execute(
            "INSERT INTO chunks (document_id, idx, text, embedding) VALUES (?, 0, 'hi', ?)",
            (doc_id, b"\x00" * 16),
        )
        conn.commit()
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 0
    finally:
        conn.close()


def test_settings_defaults_from_code_not_env():
    settings = Settings(_env_file=None)
    assert settings.groq_model == "openai/gpt-oss-120b"
    assert settings.groq_base_url == "https://api.groq.com/openai/v1"
    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.chunk_size == 900
    assert settings.chunk_overlap == 150
    assert settings.top_k == 5
    assert settings.max_upload_mb == 10
    assert settings.max_chunks_per_document == 2000
