from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 5
    max_upload_mb: int = 10
    max_chunks_per_document: int = 2000
    history_limit: int = 10
    db_path: Path = BASE_DIR / "data" / "app.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
