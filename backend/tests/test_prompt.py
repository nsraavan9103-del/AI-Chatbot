from app.prompt import SYSTEM_PROMPT, build_messages
from app.retrieval import Hit


def _hit(chunk_id=1, filename="a.pdf", idx=0, text="some text", score=0.9):
    return Hit(chunk_id, 1, filename, idx, text, score)


def test_prompt_numbers_sources_and_includes_filenames():
    messages = build_messages("what is it?", [_hit(1, "a.pdf", 0), _hit(2, "b.docx", 3)])
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == SYSTEM_PROMPT
    user = messages[1]["content"]
    assert "[1]" in user and "[2]" in user
    assert "a.pdf" in user and "b.docx" in user
    assert "what is it?" in user


def test_prompt_empty_hits_still_builds_messages():
    messages = build_messages("anything?", [])
    assert len(messages) == 2
    assert "No context available." in messages[1]["content"]


def test_prompt_instructs_dont_know():
    assert "I don't know based on the uploaded documents." in SYSTEM_PROMPT
