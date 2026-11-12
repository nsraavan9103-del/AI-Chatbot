from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    char_count: int
    chunk_count: int
    created_at: str


class ChatOut(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    message_count: int


class SourceOut(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    idx: int
    snippet: str
    score: float


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str
    sources: list[SourceOut]
    mode: str | None = None
