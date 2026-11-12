import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class FakeEmbedder:
    def embed_documents(self, texts):
        return np.stack([np.eye(4)[len(text) % 4] for text in texts]).astype(np.float32)

    def embed_query(self, text):
        return np.array([1, 0, 0, 0], dtype=np.float32)


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, db_path=tmp_path / "test.db")


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def fake_llm_stream():
    return lambda messages: iter(["Hello", " world"])


@pytest.fixture
def client(settings, fake_embedder, fake_llm_stream):
    app = create_app(settings, embedder=fake_embedder, llm_stream=fake_llm_stream)
    return TestClient(app)
