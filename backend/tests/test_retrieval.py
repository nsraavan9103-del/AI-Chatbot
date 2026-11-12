import numpy as np
import pytest

from app.db import connect, init_db
from app.embeddings import decode_vector, encode_vector
from app.retrieval import search


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    connection = connect(db_path)
    connection.execute(
        "INSERT INTO documents (filename, content_type, size_bytes, char_count, chunk_count)"
        " VALUES ('doc.txt', 'text/plain', 10, 10, 3)"
    )
    yield connection
    connection.close()


def _insert_chunks(conn, vectors):
    for idx, vec in enumerate(vectors):
        conn.execute(
            "INSERT INTO chunks (document_id, idx, text, embedding) VALUES (1, ?, ?, ?)",
            (idx, f"chunk {idx}", encode_vector(np.array(vec, dtype=np.float32))),
        )
    conn.commit()


def test_search_ranks_by_cosine(conn):
    _insert_chunks(conn, [[1, 0, 0, 0], [0, 1, 0, 0], [0.7, 0.7, 0, 0]])
    hits = search(conn, np.array([1, 0, 0, 0], dtype=np.float32), top_k=3)
    assert [hit.chunk_id for hit in hits] == [1, 3, 2]


def test_search_respects_top_k(conn):
    _insert_chunks(conn, [[1, 0, 0, 0], [0, 1, 0, 0], [0.7, 0.7, 0, 0]])
    assert len(search(conn, np.array([1, 0, 0, 0], dtype=np.float32), top_k=2)) == 2


def test_search_empty_table_returns_empty(conn):
    assert search(conn, np.array([1, 0, 0, 0], dtype=np.float32), top_k=5) == []


def test_vector_roundtrip():
    vec = np.array([1.5, -2.0, 0.25], dtype=np.float32)
    assert np.array_equal(decode_vector(encode_vector(vec)), vec)


def test_vector_roundtrip_coerces_float64():
    vec = np.eye(4)[0]
    assert vec.dtype == np.float64
    decoded = decode_vector(encode_vector(vec))
    assert decoded.dtype == np.float32
    assert np.array_equal(decoded, np.array([1, 0, 0, 0], dtype=np.float32))
