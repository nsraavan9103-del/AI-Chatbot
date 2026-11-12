import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.db import connect
from app.deps import get_db
from app.prompt import build_messages
from app.retrieval import search
from app.schemas import ChatOut, MessageOut, SourceOut

router = APIRouter()

CANNED_EMPTY_REPLY = "I don't have any documents yet — upload one first."
SNIPPET_CHARS = 300


class ChatCreate(BaseModel):
    title: str = "New chat"


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)


def _chat_row(conn: sqlite3.Connection, chat_id: int):
    return conn.execute(
        "SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.chat_id = c.id)"
        " AS message_count FROM chats c WHERE c.id = ?",
        (chat_id,),
    ).fetchone()


def _save_assistant(conn, chat_id: int, content: str, hits) -> int:
    cursor = conn.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, 'assistant', ?)",
        (chat_id, content),
    )
    message_id = cursor.lastrowid
    conn.executemany(
        "INSERT INTO message_sources (message_id, chunk_id, rank, score)"
        " VALUES (?, ?, ?, ?)",
        [
            (message_id, hit.chunk_id, rank, hit.score)
            for rank, hit in enumerate(hits, start=1)
        ],
    )
    conn.execute("UPDATE chats SET updated_at = datetime('now') WHERE id = ?", (chat_id,))
    conn.commit()
    return message_id


@router.get("/chats", response_model=list[ChatOut])
def list_chats(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(
        "SELECT c.*, COUNT(m.id) AS message_count FROM chats c"
        " LEFT JOIN messages m ON m.chat_id = c.id"
        " GROUP BY c.id ORDER BY c.updated_at DESC, c.id DESC"
    ).fetchall()
    return [ChatOut(**dict(row)) for row in rows]


@router.post("/chats", status_code=201, response_model=ChatOut)
def create_chat(payload: ChatCreate, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute("INSERT INTO chats (title) VALUES (?)", (payload.title,))
    conn.commit()
    return ChatOut(**dict(_chat_row(conn, cursor.lastrowid)))


@router.delete("/chats/{chat_id}", status_code=204)
def delete_chat(chat_id: int, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Chat not found")
    return Response(status_code=204)


@router.get("/chats/{chat_id}/messages", response_model=list[MessageOut])
def list_messages(chat_id: int, conn: sqlite3.Connection = Depends(get_db)):
    if conn.execute("SELECT 1 FROM chats WHERE id = ?", (chat_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    rows = conn.execute(
        "SELECT * FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,)
    ).fetchall()
    messages = []
    for row in rows:
        sources = conn.execute(
            "SELECT ms.chunk_id, ms.score, c.document_id, c.idx, c.text, d.filename"
            " FROM message_sources ms"
            " JOIN chunks c ON c.id = ms.chunk_id"
            " JOIN documents d ON d.id = c.document_id"
            " WHERE ms.message_id = ? ORDER BY ms.rank",
            (row["id"],),
        ).fetchall()
        messages.append(
            MessageOut(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
                sources=[
                    SourceOut(
                        chunk_id=source["chunk_id"],
                        document_id=source["document_id"],
                        filename=source["filename"],
                        idx=source["idx"],
                        snippet=source["text"][:SNIPPET_CHARS],
                        score=source["score"],
                    )
                    for source in sources
                ],
            )
        )
    return messages


@router.post("/chats/{chat_id}/messages")
def create_message(chat_id: int, payload: MessageCreate, request: Request):
    settings = request.app.state.settings
    embedder = request.app.state.embedder
    llm_stream = request.app.state.llm_stream
    db_path = settings.db_path

    check = connect(db_path)
    try:
        if check.execute("SELECT 1 FROM chats WHERE id = ?", (chat_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Chat not found")
    finally:
        check.close()

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    def generate():
        conn = connect(db_path)
        sources_sent = False
        try:
            conn.execute(
                "INSERT INTO messages (chat_id, role, content) VALUES (?, 'user', ?)",
                (chat_id, payload.content),
            )
            title = conn.execute(
                "SELECT title FROM chats WHERE id = ?", (chat_id,)
            ).fetchone()["title"]
            if title == "New chat":
                conn.execute(
                    "UPDATE chats SET title = ? WHERE id = ?",
                    (payload.content[:60], chat_id),
                )
            conn.execute(
                "UPDATE chats SET updated_at = datetime('now') WHERE id = ?", (chat_id,)
            )
            conn.commit()

            hits = search(conn, embedder.embed_query(payload.content), settings.top_k)
            yield sse(
                "sources",
                {
                    "sources": [
                        {
                            "chunk_id": hit.chunk_id,
                            "document_id": hit.document_id,
                            "filename": hit.filename,
                            "idx": hit.idx,
                            "snippet": hit.text[:SNIPPET_CHARS],
                            "score": hit.score,
                        }
                        for hit in hits
                    ]
                },
            )
            sources_sent = True

            has_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] > 0
            if not has_chunks:
                message_id = _save_assistant(conn, chat_id, CANNED_EMPTY_REPLY, [])
                yield sse("token", {"text": CANNED_EMPTY_REPLY})
                yield sse("done", {"message_id": message_id})
                return

            collected = []
            for token in llm_stream(build_messages(payload.content, hits)):
                collected.append(token)
                yield sse("token", {"text": token})
            message_id = _save_assistant(conn, chat_id, "".join(collected), hits)
            yield sse("done", {"message_id": message_id})
        except Exception as exc:
            conn.rollback()
            if not sources_sent:
                yield sse("sources", {"sources": []})
            yield sse("error", {"message": str(exc)})
        finally:
            conn.close()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
