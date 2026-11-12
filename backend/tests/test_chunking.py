import pytest

from app.chunking import chunk_text


def test_short_text_single_chunk():
    assert chunk_text("hello world") == ["hello world"]


def test_long_text_splits_under_size():
    text = "word " * 500
    chunks = chunk_text(text, size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_chunks_share_overlap():
    text = "abcdefghij" * 40
    chunks = chunk_text(text, size=100, overlap=20)
    for previous, following in zip(chunks, chunks[1:]):
        assert previous[-20:] == following[:20]


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        chunk_text("hello", size=10, overlap=10)


def test_no_whitespace_only_chunks():
    chunks = chunk_text("first\n\n   \n\n\n\nsecond\n\n\t\n\n", size=100, overlap=10)
    assert chunks
    assert all(chunk.strip() for chunk in chunks)


def test_paragraph_boundaries_preferred():
    text = "a" * 30 + "\n\n" + "b" * 30
    assert chunk_text(text, size=900, overlap=150) == [text]
