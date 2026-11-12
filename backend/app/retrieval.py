import sqlite3
from typing import NamedTuple

import numpy as np

from app.embeddings import decode_vector


class Hit(NamedTuple):
    chunk_id: int
    document_id: int
    filename: str
    idx: int
    text: str
    score: float


def search(conn: sqlite3.Connection, query_vec: np.ndarray, top_k: int) -> list[Hit]:
    if top_k <= 0:
        return []
    rows = conn.execute(
        "SELECT c.id, c.document_id, d.filename, c.idx, c.text, c.embedding"
        " FROM chunks c JOIN documents d ON d.id = c.document_id"
    ).fetchall()
    if not rows:
        return []
    matrix = np.stack([decode_vector(row["embedding"]) for row in rows])
    scores = matrix @ np.asarray(query_vec, dtype=np.float32)
    order = np.argsort(-scores)[:top_k]
    return [
        Hit(
            rows[i]["id"],
            rows[i]["document_id"],
            rows[i]["filename"],
            rows[i]["idx"],
            rows[i]["text"],
            float(scores[i]),
        )
        for i in order
    ]
