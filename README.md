# AI-Chatbot

Upload your documents and ask questions. Answers that come from your files cite the
passage they came from; questions your files cannot answer are answered from general
knowledge and labelled as such.

## Features

- Upload PDF, DOCX, TXT and Markdown; each file is extracted, chunked and embedded locally.
- Answers cite their sources as `[1]`, `[2]`, with a Sources panel listing filename, part and score.
- Questions your documents do not cover are answered from general knowledge, labelled `General knowledge`.
- Follow-up questions work: the last 10 messages of the chat are sent as context.
- Answers stream token by token over SSE.
- Everything persists in SQLite. Single local user, no accounts.

## Stack

FastAPI + SQLite on the backend, React + Vite on the frontend, Groq for
generation, and `all-MiniLM-L6-v2` running locally for embeddings.

## Setup

Requires Python 3.13, Node 26 / npm 11, and a Groq API key.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

On macOS/Linux the interpreter is `.venv/bin/python`.

Copy `.env.example` to `.env` and add a key from
[console.groq.com/keys](https://console.groq.com/keys):

```dotenv
GROQ_API_KEY=your_key_here
```

Start the API from the repo root:

```bash
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --app-dir backend --port 8000
```

Start the UI in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to `127.0.0.1:8000`.

## Tests

```bash
cd backend && ../.venv/Scripts/python.exe -m pytest -q   # 60 tests, offline
cd frontend && npm run build && npm run lint
```

## Project structure

```
backend/app/       FastAPI app: config, db, extraction, chunking, embeddings, retrieval, prompt, routes
backend/tests/     pytest suite (offline: no Groq call, no model download)
frontend/src/      React app: api client, chat shell, uploads, sources
data/app.db        SQLite database (git-ignored, disposable)
```

## How it works

An upload is extracted to text, split into ~900-character chunks, embedded with a local
MiniLM model, and stored as float32 vectors in SQLite. A question is embedded the same way
and cosine-ranked against every chunk with NumPy; the top five become context for Groq,
which streams back an answer over SSE. An answer that cites a supplied chunk is recorded as
`documents` and keeps its Sources; one that does not is recorded as `general` and shows no
sources. The first upload downloads ~90 MB of MiniLM once. `data/app.db` is disposable:
delete it to reset, and re-upload after changing the embedding model.
