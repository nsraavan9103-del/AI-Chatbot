import json

import numpy as np
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


def test_assistant_message_persisted_with_sources(settings, fake_embedder):
    client = TestClient(
        create_app(
            settings,
            embedder=fake_embedder,
            llm_stream=lambda m: iter(["According to [1], it is 4.2 million."]),
        )
    )
    _upload(client)
    chat = _chat(client)
    _send(client, chat["id"])
    messages = client.get(f"/api/chats/{chat['id']}/messages").json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "According to [1], it is 4.2 million."
    assert len(messages[1]["sources"]) >= 1
    assert messages[1]["sources"][0]["filename"] == "a.txt"
    assert messages[1]["mode"] == "documents"


def test_first_message_titles_the_chat(client):
    _upload(client)
    chat = _chat(client)
    _send(client, chat["id"], "What is the main claim of this article?")
    assert client.get("/api/chats").json()[0]["title"] == "What is the main claim of this article?"


def test_empty_library_answers_from_general_knowledge(settings, fake_embedder):
    calls = []

    def recording_stream(messages):
        calls.append(messages)
        return iter(["Paris is the capital of France."])

    client = TestClient(create_app(settings, embedder=fake_embedder, llm_stream=recording_stream))
    chat = _chat(client)
    body = _send(client, chat["id"])
    assert len(calls) == 1
    assert "event: sources" in body
    assert "event: token" in body
    assert "event: done" in body
    messages = client.get(f"/api/chats/{chat['id']}/messages").json()
    assert messages[1]["mode"] == "general"
    assert messages[1]["sources"] == []


def test_document_answer_is_labelled_documents(settings, fake_embedder):
    client = TestClient(
        create_app(
            settings,
            embedder=fake_embedder,
            llm_stream=lambda m: iter(["According to [1], it is 4.2 million."]),
        )
    )
    _upload(client)
    chat = _chat(client)
    _send(client, chat["id"])
    messages = client.get(f"/api/chats/{chat['id']}/messages").json()
    assert messages[1]["mode"] == "documents"
    assert messages[1]["sources"] != []


def test_general_answer_is_labelled_general(settings, fake_embedder):
    client = TestClient(
        create_app(settings, embedder=fake_embedder, llm_stream=lambda m: iter(["Hello", " world"]))
    )
    _upload(client)
    chat = _chat(client)
    _send(client, chat["id"])
    messages = client.get(f"/api/chats/{chat['id']}/messages").json()
    assert messages[1]["mode"] == "general"
    assert messages[1]["sources"] == []


def test_follow_up_includes_prior_turns(settings, fake_embedder):
    calls = []

    def recording_stream(messages):
        calls.append(messages)
        return iter(["first answer"])

    client = TestClient(create_app(settings, embedder=fake_embedder, llm_stream=recording_stream))
    _upload(client)
    chat = _chat(client)
    _send(client, chat["id"], "first question")
    _send(client, chat["id"], "and the second one?")
    assert len(calls) == 2
    second = calls[1]
    assert second[0]["role"] == "system"
    assert [m["role"] for m in second] == ["system", "user", "assistant", "user"]
    assert second[1]["content"] == "first question"
    assert second[2]["content"] == "first answer"
    assert "and the second one?" in second[3]["content"]


def test_user_messages_have_null_mode(client):
    _upload(client)
    chat = _chat(client)
    _send(client, chat["id"])
    messages = client.get(f"/api/chats/{chat['id']}/messages").json()
    assert messages[0]["mode"] is None


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


def test_embed_failure_emits_sources_then_error(settings):
    class BrokenEmbedder:
        def embed_documents(self, texts):
            return np.zeros((len(texts), 4), dtype=np.float32)

        def embed_query(self, text):
            raise RuntimeError("embed failed")

    client = TestClient(
        create_app(settings, embedder=BrokenEmbedder(), llm_stream=lambda m: iter(["x"]))
    )
    _upload(client)
    chat = _chat(client)
    body = _send(client, chat["id"])
    assert body.index("event: sources") < body.index("event: error")
    assert "embed failed" in body


def _sse_events(body):
    events = {}
    for block in body.split("\n\n"):
        lines = [line for line in block.split("\n") if line]
        if not lines:
            continue
        name = lines[0].split(": ", 1)[1]
        events.setdefault(name, []).append(json.loads(lines[1].split(": ", 1)[1]))
    return events


def test_snippet_is_truncated_to_300_chars(settings, fake_embedder):
    client = TestClient(
        create_app(
            settings,
            embedder=fake_embedder,
            llm_stream=lambda m: iter(["According to [1], yes."]),
        )
    )
    _upload(client, data=("x" * 400).encode())
    chat = _chat(client)
    body = _send(client, chat["id"])
    sse_sources = _sse_events(body)["sources"][0]["sources"]
    assert len(sse_sources[0]["snippet"]) == 300
    messages = client.get(f"/api/chats/{chat['id']}/messages").json()
    assert len(messages[1]["sources"][0]["snippet"]) == 300


def test_sse_response_headers(client):
    _upload(client)
    chat = _chat(client)
    with client.stream(
        "POST", f"/api/chats/{chat['id']}/messages", json={"content": "hi"}
    ) as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"
        "".join(response.iter_text())


def test_unknown_chat_is_404(client):
    assert client.post("/api/chats/999/messages", json={"content": "hi"}).status_code == 404


def test_empty_message_is_422(client):
    chat = _chat(client)
    assert client.post(f"/api/chats/{chat['id']}/messages", json={"content": ""}).status_code == 422


def test_old_cited_answer_survives_document_delete(settings, fake_embedder):
    client = TestClient(
        create_app(
            settings,
            embedder=fake_embedder,
            llm_stream=lambda m: iter(["According to [1], it is 4.2 million."]),
        )
    )
    document_id = _upload(client).json()["documents"][0]["id"]
    chat = _chat(client)
    _send(client, chat["id"])
    assert client.get(f"/api/chats/{chat['id']}/messages").json()[1]["sources"] != []
    assert client.delete(f"/api/documents/{document_id}").status_code == 204
    messages = client.get(f"/api/chats/{chat['id']}/messages").json()
    assert messages[1]["content"] == "According to [1], it is 4.2 million."
    assert messages[1]["sources"] == []


def test_stream_answer_without_key_raises():
    settings = Settings(_env_file=None, groq_api_key="")
    with pytest.raises(RuntimeError):
        list(stream_answer([], settings))
