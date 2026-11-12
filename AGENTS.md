# AGENTS.md

## What this is

Single-file Streamlit app (`main.py`, ~245 lines). Ingestion: news URLs via newspaper3k, PDFs via PyMuPDF (`fitz`), DOCX via python-docx. Each source becomes one LangChain `Document`; a `RecursiveCharacterTextSplitter` (chunk 1000 / overlap 100) fills `st.session_state.chunks`, but nothing reads it. Q&A (`load_qa_chain`, `stuff`) and summaries (`load_summarize_chain`, `stuff`) loop over whole articles one at a time. Model: local `google/flan-t5-large` on CPU (`device=-1`, `max_length=600`), loaded once via `@st.cache_resource`. Analytics: TextBlob polarity and a word-frequency `Counter`, rendered with matplotlib. No persistence, retrieval, embeddings, or vector store.

The planned replacement — a Groq + FastAPI + SQLite + React RAG chatbot in `backend/` and `frontend/` — is specified in `.opencode/plans/2026-11-12-groq-rag-chatbot.md`. Until it lands, `main.py` is the only running app.

## Context — read this first

- Before a larger task, read `graphify-out/GRAPH_REPORT.md` in full (50 nodes / 39 edges / 14 communities; generated 2026-11-12).
- Ask the graph before grepping, from the repo root (verified with graphify 0.9.71):
  - `graphify query "<question>"` — BFS context; add `--budget 1500` to cap output.
  - `graphify explain "<symbol>"` — one node's source location and edges.
- Never read `.ua/knowledge-graph.json` or `graphify-out/graph.json` directly. They are large generated JSON; use the commands above or the Understand-Anything dashboard instead.
- Both graphs were built from `main.py` + `README.md` + `requirements.txt` and are coarse (no embeddings). Verify anything you act on against `main.py`. The Understand-Anything tour (its onboarding guide) is stale in places: it claims `flan-t5-base`, PyPDF2/pdfplumber, Plotly, scikit-learn, map-reduce summaries, and `ConversationBufferMemory`; none match the current code.

## Build/review protocol

Every task is built by one model and reviewed by a different one. A model never reviews its own work, and one task never uses the same model for both roles.

| Area | Paths | Build with | Review with |
|---|---|---|---|
| **Backend** | `backend/`, `data/`, `main.py` | `opencode-go/deepseek-v4.1-flash` — DeepSeek V4.1 Flash 1017 | `opencode-go/muse-spark-1.3-contributor` — Muse Spark 1.3 Contributor |
| **Frontend** | `frontend/` | `opencode-go/muse-spark-1.3-contributor` — Muse Spark 1.3 Contributor | `opencode-go/deepseek-v4.1-flash` — DeepSeek V4.1 Flash 1017 |
| **Docs & config** | `README.md`, `AGENTS.md`, `.env.example`, `.gitignore` | the model that owns the code the doc describes | the other model |

The model pinned in an agent file is not automatically the protocol's builder. Set the model on every dispatch:

| Role | Route |
|---|---|
| Backend build | `subagent`, `agent: "general"`, `model: "opencode-go/deepseek-v4.1-flash"`, prompt = one task from the plan |
| Backend review | `subagent`, `agent: "general"`, `model: "opencode-go/muse-spark-1.3-contributor"`, prompt = review brief |
| Frontend build | `subagent`, `agent: "frontend-implementer"`, `model: "opencode-go/muse-spark-1.3-contributor"`, prompt = slice brief |
| Frontend review | `subagent`, `agent: "frontend-reviewer"`, `model: "opencode-go/deepseek-v4.1-flash"`, prompt = review brief |

`build-pro` and `frontend-orchestrator` are primary agents; dispatch `general`, `frontend-implementer` or `frontend-reviewer` instead. If a role's model is unavailable, stop and say so. Never fall back to the same model for build and review, and never let a session's default model fill the second role.

## Workflow

1. **Split by area.** Write the work as separate backend and frontend tasks. A task that needs a new endpoint is two tasks: backend first (it defines the contract), frontend second (it consumes the contract). Never one task that edits both trees.
2. **Plan.** `plan-pro` writes `.opencode/plans/<YYYY-MM-DD>-<slug>.md`: per-task files, interfaces, exact checks, and the baseline results before any edit.
3. **Build one task at a time** with the area's build model. Test-first for backend logic. Smallest change that fully solves the task. Run the task's checks before returning, and report only checks that actually ran.
4. **Hand off.** Give the reviewer: the diff, the owned-file list, the contract, the baseline, and the skill IDs to load.
5. **Review** with the area's review model, read-only. The reply starts with `VERDICT: CLEAN` or `VERDICT: CHANGES REQUESTED`, then findings `F1..Fn`, each with `file:line`, why it matters, and a concrete fix. Issues that predate the change go in a separate "pre-existing" list.
6. **Fix** with the build model. Apply each finding or say in one line why not. Re-run the checks. If the fix touched flagged lines, ask the reviewer to re-check only those findings.
7. **Ship.** Run the area's checks below, then commit with a Conventional Commit message.

### Checks per area

Run these before review and again after fixes.

| Area | From | Commands |
|---|---|---|
| Backend | `backend/` | `../.venv/Scripts/python.exe -m pytest -q` and `../.venv/Scripts/python.exe -m pip check` |
| Frontend | `frontend/` | `npm run build`, plus `npm run lint` when `package.json` defines it |
| Both | repo root | `git status --short` — only intended files, no `data/`, `node_modules/`, `dist/`, `__pycache__` |

Legacy Streamlit checks stay as documented under Commands: `compileall` and the `AppTest` smoke test.

### Task brief template

```text
Area: backend | frontend
Build model: <from the table>   Review model: <the other one>
Files I own: <paths — nothing outside these>
Contract: <endpoints, schemas, exact copy>
Done when: <checkable criteria>
Checks: <exact commands>
Baseline: <results before any edit>
Skills: <IDs to load>
```

## Skills per task

Always in force: the karpathy guidelines instruction file, and `project-lessons` when the skill exists.

If a listed skill is not installed for this project, say which one and carry on with the rest. Never guess a skill's contents.

| When | Load | Who |
|---|---|---|
| New or underspecified request, before planning | `brainstorming` | planner |
| Design agreed, before any code | `writing-plans` | planner |
| Working through an approved plan | `executing-plans` (inline) or `subagent-driven-development` (task per subagent) | planner / builder |
| Writing backend logic | `test-driven-development` — failing test first | backend build |
| Any failing check or unexpected behaviour | `systematic-debugging` — before proposing a fix | both builds |
| Any code change | `ponytail` — smallest change that fully solves the task | both builds |
| Before claiming a task is done | `verification-before-completion` | both builds |
| Handing work to review | `requesting-code-review` | both builds |
| Acting on findings | `receiving-code-review` | both builds |
| Interface work: layout, components, colour, type, a11y | `ui-ux-pro-max` | frontend |
| Any new or restyled screen, or a page that looks templated | `design-taste-frontend` (tasteskill v2), full run | frontend |
| Reviewing a diff | `caveman-review` for compressed findings, `ponytail-review` for logic, safety, load, tests and speed | both reviews |
| Checking a page in a real browser | `playwright-cli` | frontend review |
| Default reply register | `caveman` — see Token discipline | anyone |
| Output over ~20 lines: test runs, logs, big files, JSON | context-mode tools (`ctx_batch`, `ctx_execute`, `ctx_search`) instead of raw output | anyone |

### Stack by area

- **Backend build:** `ponytail` → `test-driven-development` → `systematic-debugging` on failure → `verification-before-completion` → `requesting-code-review`; context-mode for test output.
- **Backend review:** `caveman-review` → `ponytail-review`; findings only, never edits.
- **Frontend build:** `ui-ux-pro-max` → `design-taste-frontend` → `ponytail` → `verification-before-completion`.
- **Frontend review:** `frontend-reviewer` brief → `caveman-review` → `playwright-cli` for the rendered result.

## Token discipline — caveman

Turn Caveman on wherever it is safe, to cut output tokens. It never changes code quality: same edits, same tests, same checks, same full identifiers.

**On by default:** chat replies, progress updates, status lines, summaries of what changed, and review findings — load `caveman`, or `caveman-review` for a diff review. Compress the prose, never the facts.

**Always off:**
- code, diffs, commit bodies, and file paths;
- commands, test names, error messages, stack traces, and API contracts;
- design docs and plans the person must read to decide (`brainstorming`, `writing-plans`);
- security notes, destructive-operation confirmations, and anything where a missing qualifier would change a decision.

**Never abbreviated, even in caveman:** `def`/identifier names, JSON keys, HTTP verbs and status codes, model IDs, versions, and numbers.

The other lever is context-mode: when a command's output will exceed ~20 lines (test runs, logs, large files, JSON), route it through `ctx_execute` / `ctx_batch` and print only the answer, rather than pasting the raw result into the conversation.

## Commands

Run from the repo root. `.venv/Scripts/python.exe` (Python 3.13.5) is the app's only working interpreter; `pip check` passes.

- **Install / restore** — the checked-in `.venv` is the source of truth. `pip install -r requirements.txt` fails on Python 3.13 (`faiss-cpu==1.7.4` has no wheel) and its pins would downgrade working imports. Recreate with the versions actually installed:
  ```bash
  .venv/Scripts/python.exe -m pip install "streamlit==1.50.0" "langchain==0.3.27" "langchain-community==0.3.30" "langchain-core==0.3.76" "transformers==4.56.2" "torch==2.8.0" "textblob==0.19.0" "matplotlib==3.10.6" "newspaper3k==0.2.8" "python-docx==1.2.0" "PyMuPDF==1.26.4"
  .venv/Scripts/python.exe -m pip check   # -> No broken requirements found.
  ```
- **Dev** — `.venv/Scripts/python.exe -m streamlit run main.py`. Add `--server.headless true --server.port 8599` for agent runs; `GET /_stcore/health` returns `ok` when ready. Never call `.venv/Scripts/streamlit.exe`: it exits 1 with no output.
- **Build** — none; single-file Python, no packaging step. Quick syntax check: `.venv/Scripts/python.exe -m compileall -q main.py`.
- **Test** — no suite, linter, typecheck, or CI. Smoke-test all three pages with Streamlit's `AppTest` (no model download):
  ```bash
  .venv/Scripts/python.exe -c "
  from streamlit.testing.v1 import AppTest
  at = AppTest.from_file('main.py', default_timeout=60)
  for page in [None, 'Q&A and Summaries', 'Analytics Dashboard']:
      if page: at.radio[0].set_value(page)
      at.run(); print(page, at.exception)
  "
  ```
  `ElementList()` per page means no exceptions. `default_timeout=60` is required; the 3s default is exceeded by the torch/transformers imports. Never trigger the real Q&A/summarize path in a check: it downloads multi-GB `flan-t5-large` and runs on CPU.

## Dependencies

- `requirements.txt` is stale and untrusted: it pins `langchain==0.0.284`, `streamlit==1.22.0`, and `openai==0.28.0`, while `main.py` uses the langchain 0.3 API (`load_qa_chain`, `langchain.docstore.document`, `langchain_community`). Don't relax or "fix" pins without testing the app.
- Declared but unused by `main.py`: `faiss-cpu`, `openai`, `tiktoken`, `unstructured`, `libmagic`, `python-magic`, `python-magic-bin`, `python-dotenv`.
- `.env` holds `HUGGINGFACEHUB_API_TOKEN`, but `main.py` never loads environment variables (no `dotenv`) and the model runs locally; it is unused.

## Code conventions

- Navigation is a module-level `st.sidebar.radio` with `if / elif` blocks; the whole script reruns on every interaction. A new page means one radio option plus one `elif`.
- "Fetch and Process Content" clears `articles`, `chunks`, `sentiments`, `keywords`, `queries`, and `answers` before ingesting, so re-ingesting destroys earlier sources and history.
- `st.session_state.chunks` is populated but never read: Q&A and summaries run over whole `articles`. Don't build chunk retrieval on it without changing the QA path.
- `load_model_and_pipeline` is `@st.cache_resource` and is called only on the Q&A page when articles exist.
- Charts are matplotlib (`st.pyplot`), not Plotly; keywords are a `Counter` over `re.findall(r"\b\w+\b", ...)` minus a hardcoded stoplist, not scikit-learn.

## Repo gotchas

- `.gitignore` is a whitelist (`/*` plus `README.md`, `main.py`, `requirements.txt`, `.gitignore`). New files are ignored by default and won't appear in `git status`; add a `!` exception if they should be tracked. `AGENTS.md` itself is ignored/untracked.
- `notebooks/`, `faiss_store_hf/`, `faiss_store_offline.pkl`, `Screenshots/`, `Documentation/` are coursework/experiment artifacts, not used by the running app; FAISS code appears only in `notebooks/`.
- `graphify-out/` and `.ua/` are generated by the graphify/understand skills; regenerate them, don't hand-edit.
