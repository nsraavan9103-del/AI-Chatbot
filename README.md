
# 📰 News Research Chatbot + Analytics Dashboard

A powerful, user-friendly news research tool designed for effortless information retrieval and analysis. Ingest articles from URLs or upload local documents (PDF/DOCX) to ask questions, generate summaries, and visualize data trends.

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