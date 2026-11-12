from app.prompt import SYSTEM_PROMPT, build_messages, derive_mode
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


def test_prompt_allows_general_knowledge():
    assert "answer from your own general knowledge" in SYSTEM_PROMPT
    assert "Cite only the numbers that appear in the Context" in SYSTEM_PROMPT
    assert "I don't know based on the uploaded documents." not in SYSTEM_PROMPT


def test_build_messages_places_history_between_system_and_question():
    history = [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
    ]
    messages = build_messages("second question", [_hit()], history)
    assert messages[0]["role"] == "system"
    assert messages[1:3] == history
    assert messages[-1]["role"] == "user"
    assert "second question" in messages[-1]["content"]
    assert len(messages) == 4


def test_build_messages_without_history_is_two_messages():
    assert len(build_messages("q", [_hit()])) == 2


def test_derive_mode_documents_when_citing_supplied_source():
    assert derive_mode("[1] yes", 2) == "documents"


def test_derive_mode_general_when_citation_out_of_range():
    assert derive_mode("[7] yes", 2) == "general"


def test_derive_mode_general_without_citations():
    assert derive_mode("Paris is the capital.", 2) == "general"


def test_derive_mode_general_when_no_sources():
    assert derive_mode("[1] yes", 0) == "general"


def test_derive_mode_accepts_fullwidth_brackets():
    assert derive_mode("Oil prices rose to $100【1】.", 2) == "documents"
    assert derive_mode("Oil prices rose to $100［1］.", 2) == "documents"
