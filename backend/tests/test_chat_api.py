import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.llm import stream_answer
from app.main import create_app


def _upload(client, name="a.txt", data=b"hello world"):
    return client.post("/api/documents", files={"files": (name, data, "text/plain")})


def _chat(client, title=None):
    payload = {"title": title} if title is not None else {}
    return client.post("/api/chats", json=payload).json()


def _send(client, chat_id, content="what is it?"):
    with client.stream(
        "POST", f"/api/chats/{chat_id}/messages", json={"content": content}
    ) as response:
        return "".join(response.iter_text())


def test_create_and_delete_chat(client):
    chat = _chat(client)
    assert chat["title"] == "New chat"
    assert chat["message_count"] == 0
    assert [c["id"] for c in client.get("/api/chats").json()] == [chat["id"]]
    assert client.delete(f"/api/chats/{chat['id']}").status_code == 204
    assert client.get("/api/chats").json() == []


def test_sse_event_order_and_payload(client):
    _upload(client)
    chat = _chat(client)
    body = _send(client, chat["id"])
    assert body.index("event: sources") < body.index("event: token")
    assert body.index("event: token") < body.index("event: done")
    assert "Hello" in body


def test_assistant_message_persisted_with_sources(client):
    _upload(client)
    chat = _chat(client)
    _send(client, chat["id"])
    messages = client.get(f"/api/chats/{chat['id']}/messages").json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "Hello world"
    assert len(messages[1]["sources"]) >= 1
    assert messages[1]["sources"][0]["filename"] == "a.txt"


def test_first_message_titles_the_chat(client):
    _upload(client)
    chat = _chat(client)
    _send(client, chat["id"], "What is the main claim of this article?")
    assert client.get("/api/chats").json()[0]["title"] == "What is the main claim of this article?"


def test_empty_library_returns_canned_reply_and_skips_llm(
    settings, fake_embedder
):
    calls = []

    def recording_stream(messages):
        calls.append(messages)
        return iter(["should not happen"])

    client = TestClient(create_app(settings, embedder=fake_embedder, llm_stream=recording_stream))
    chat = _chat(client)
    body = _send(client, chat["id"])
    assert "I don't have any documents yet" in body
    assert "event: done" in body
    assert calls == []


def test_llm_error_emits_error_and_persists_no_assistant_message(
    settings, fake_embedder
):
    def broken_stream(messages):
        raise RuntimeError("boom")

    client = TestClient(create_app(settings, embedder=fake_embedder, llm_stream=broken_stream))
    _upload(client)
    chat = _chat(client)
    body = _send(client, chat["id"])
    assert "event: error" in body
    assert "boom" in body
    messages = client.get(f"/api/chats/{chat['id']}/messages").json()
    assert [m["role"] for m in messages] == ["user"]


def test_unknown_chat_is_404(client):
    assert client.post("/api/chats/999/messages", json={"content": "hi"}).status_code == 404


def test_empty_message_is_422(client):
    chat = _chat(client)
    assert client.post(f"/api/chats/{chat['id']}/messages", json={"content": ""}).status_code == 422


def test_old_cited_answer_survives_document_delete(client):
    document_id = _upload(client).json()["documents"][0]["id"]
    chat = _chat(client)
    _send(client, chat["id"])
    assert client.delete(f"/api/documents/{document_id}").status_code == 204
    messages = client.get(f"/api/chats/{chat['id']}/messages").json()
    assert messages[1]["content"] == "Hello world"
    assert messages[1]["sources"] == []


def test_stream_answer_without_key_raises():
    settings = Settings(_env_file=None, groq_api_key="")
    with pytest.raises(RuntimeError):
        list(stream_answer([], settings))
