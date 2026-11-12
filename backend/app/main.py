import functools
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.db import init_db
from app.embeddings import Embedder
from app.llm import stream_answer
from app.routes import chats, documents

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, embedder=None, llm_stream=None) -> FastAPI:
    settings = settings or get_settings()
    init_db(settings.db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not settings.groq_api_key:
            logger.warning(
                "GROQ_API_KEY is not set; questions will fail until it is configured."
            )
        yield

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.state.embedder = embedder if embedder is not None else Embedder(settings.embedding_model)
    app.state.llm_stream = (
        llm_stream if llm_stream is not None else functools.partial(stream_answer, settings=settings)
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "llm_configured": bool(settings.groq_api_key)}

    app.include_router(documents.router, prefix="/api")
    app.include_router(chats.router, prefix="/api")
    return app
