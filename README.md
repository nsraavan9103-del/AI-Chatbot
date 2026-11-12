
# 📰 News Research Chatbot + Analytics Dashboard

A powerful, user-friendly news research tool designed for effortless information retrieval and analysis. Ingest articles from URLs or upload local documents (PDF/DOCX) to ask questions, generate summaries, and visualize data trends.

## New app (React + FastAPI + Groq)

A file-upload RAG chatbot: FastAPI + SQLite on the back, React on the front, Groq for answers, local MiniLM embeddings for retrieval. The legacy Streamlit app below is untouched and still runs.

**Prerequisites:** the checked-in `.venv` (Python 3.13.5), Node 26 / npm 11, and a Groq API key.

1. **Add the key** — create one at [console.groq.com/keys](https://console.groq.com/keys) and put it in the root `.env` (copy `.env.example` to `.env` first):
   ```dotenv
   GROQ_API_KEY=your_key_here
   ```
   Without a key the API still boots; asking a question returns an `error` event instead of an answer.

2. **Run the backend** (from the repo root):
   ```bash
   .venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --app-dir backend --port 8000
   ```

3. **Run the frontend** (in a second terminal):
   ```bash
   cd frontend
   npm install   # first run only
   npm run dev   # http://localhost:5173
   ```

**Architecture:** the browser talks to the Vite dev server, which proxies `/api` to FastAPI. Uploads are extracted (PDF/DOCX/TXT/MD), chunked, embedded locally with `all-MiniLM-L6-v2`, and stored in SQLite at `data/app.db`. A question is embedded, cosine-ranked against every chunk with NumPy, and the top chunks go to Groq through the `openai` SDK; the answer streams back over SSE with numbered citations. The first upload downloads ~90 MB of MiniLM once, and `sentence-transformers` makes the first request slow while it loads. `data/app.db` is disposable — delete it to reset, and re-upload after changing the embedding model. Backend tests: `cd backend && ../.venv/Scripts/python.exe -m pytest -q`.

## Legacy Streamlit app

The sections below describe `main.py`, the original single-file Streamlit app.

## 🚀 Features

- **Multi-Source Ingestion**: Fetch articles directly from URLs or upload local PDF and DOCX files.
- **Local LLM Interaction**: Uses `google/flan-t5-large` for high-quality Question Answering and Summarization without external API costs.
- **Intelligent Summarization**: Automatically generate detailed summaries for each ingested source.
- **Analytics Dashboard**:
  - **Sentiment Analysis**: Track the emotional tone (polarity) across all ingested articles.
  - **Keyword Frequency**: Visualize the most common keywords present in the content (excluding common stop words).
  - **Query History**: Keep track of questions asked during the session.
- **Efficient Processing**: Splitting content into manageable chunks for better context handling.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd "News Research Tool"
   ```

2. **Set up a virtual environment** (Optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file in the root directory (though currently using local models, it's good practice for extensions).
   ```bash
   # Optional if adding OpenAI support later
   OPENAI_API_KEY=your_api_key_here
   ```

## 📖 Usage

1. **Launch the application**:
   ```bash
   streamlit run main.py
   ```

2. **Navigation**: Use the sidebar to switch between pages:
   - **Article Ingestion**: Paste URLs (one per line) or upload PDF/DOCX files. Click **Fetch and Process Content** to load them.
   - **Q&A and Summaries**: Type a question to find answers across all sources or click **Summarize All Articles** for quick insights.
   - **Analytics Dashboard**: View metrics, sentiment trends, and keyword visualizations.

## 📂 Project Structure

- `main.py`: The primary Streamlit application containing UI logic and LLM pipelines.
- `requirements.txt`: Project dependencies.
- `Documentation/`: Additional project notes.
- `Screenshots/`: Visual guides of the interface.
- `faiss_store_hf/`: Local storage for vector indices (if enabled).

---
*Developed for efficient news research and financial analysis.*