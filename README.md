# REPOEVOLUTION ⚡
### Software Evolution Intelligence Engine & Grounded Developer Copilot

RepoEvolution is an NLP-powered developer intelligence system that parses software repositories, builds Abstract Syntax Tree (AST) entity representations, maintains a dependency call-graph (`ChangeGraph`), and provides an evidence-grounded AI Copilot for developer Q&A.

---

## 🚀 Phase 1 Architecture & Vertical Slice

Phase 1 implements the complete core ingestion, indexing, dependency graph, REST API, and Streamlit developer interface:

1. **RepoSense AST Parser**: Native Python AST parsing via `BaseParser` abstraction for extracting classes, functions, methods, docstrings, and call dependencies.
2. **Hybrid Search Index**: Combines sparse keyword search (**BM25**) with dense semantic vector embeddings (**sentence-transformers/all-MiniLM-L6-v2** + **FAISS**) using Reciprocal Rank Fusion (RRF).
3. **ChangeGraph**: Directed dependency and call graph built using **NetworkX** to compute downstream impact propagation.
4. **SemanticDiff (Phase 2)**: AST-aware Git commit comparison engine (`GitSnapshotLoader` + `SemanticEntityDiffEngine`) classifying changes into `ADDED`, `REMOVED`, `MODIFIED`, `RENAMED`, `SIGNATURE_CHANGED`, and `DEPENDENCY_CHANGED` without modifying working tree.
5. **DriftGuard (Phase 3)**: Evidence-driven historical pattern drift engine (`HistoryAnalyzer` + `PatternExtractor` + `DriftDetectionEngine`) evaluating target commits against historical commit sequences for `DEPENDENCY_DRIFT`, `API_DRIFT`, and `STRUCTURAL_DRIFT`.
6. **Grounded Copilot**: RAG pipeline powered by **Gemini Provider** abstraction (`LLMProvider`) that forces answers to cite exact file lines (`[filepath#Lstart-Lend]`).
7. **REST API**: Asynchronous FastAPI endpoints (`/api/v1/repo/ingest`, `/api/v1/repo/search`, `/api/v1/repo/compare`, `/api/v1/repo/drift`, `/api/v1/graph/data`, `/api/v1/copilot/ask`).
8. **Streamlit UI**: Dark mode developer dashboard with interactive tabs (Overview, Search, Semantic Compare, DriftGuard, ChangeGraph, Copilot).

---

## 🛠️ Installation & Setup

### 1. Prerequisites
* Python 3.11+
* Git

### 2. Install Dependencies
```bash
git clone https://github.com/ektasingh1234/RepoEvolution.git
cd RepoEvolution

# Create virtual environment
python -m venv .venv
# Windows (PowerShell / CMD):
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
# Windows PowerShell:
Copy-Item .env.example .env
# Linux / macOS / Bash:
cp .env.example .env
```
Edit `.env` to supply your **Google Gemini API Key**:
```env
GEMINI_API_KEY=your_actual_gemini_api_key
DEFAULT_GEMINI_MODEL=gemini-2.5-flash
```

---

## 🏃 Running the Application

### Option A: Launch Streamlit Developer Interface
```bash
streamlit run ui/app.py
```
Open your browser at `http://localhost:8501`.

### Option B: Launch FastAPI Backend Server
```bash
uvicorn src.api.main:app --reload --port 8000
```
* **Interactive API Documentation (Swagger)**: `http://localhost:8000/docs`
* **Alternative API Documentation (ReDoc)**: `http://localhost:8000/redoc`

---

## 🧪 Running Automated Tests

Run the complete Pytest suite for Phase 1:
```bash
# Windows:
.\.venv\Scripts\python.exe -m pytest -v
# Linux/macOS:
.venv/bin/pytest -v
```

---

## 📁 Repository Structure

```
RepoEvolution/
├── prompts/                      # Externalized Version-Controlled Prompts
│   ├── system_copilot.txt        # Grounded system prompt for Copilot
│   ├── prompt_rationale.txt      # Evolutionary rationale extraction prompt
│   └── prompt_drift.txt          # Documentation & test drift prompt
├── src/
│   ├── core/
│   │   ├── config.py             # Settings & Environment Loader
│   │   └── models.py             # Pydantic schemas (CodeEntity, Search, Copilot)
│   ├── reposense/
│   │   ├── base_parser.py        # Abstract Base Parser interface
│   │   ├── python_parser.py      # Native Python AST Parser implementation
│   │   └── indexer.py            # BM25 + FAISS Hybrid Retrieval Index
│   ├── changegraph/
│   │   └── graph_builder.py      # NetworkX call & dependency graph builder
│   ├── copilot/
│   │   └── llm_provider.py       # LLMProvider base & GeminiProvider implementation
│   └── api/
│       ├── main.py               # FastAPI entrypoint
│       └── routes/               # Modular REST endpoints
├── ui/
│   ├── app.py                    # Streamlit Developer Dashboard
│   └── styles.py                 # Custom dark theme glassmorphism CSS
├── tests/                        # Pytest suite
│   ├── test_python_parser.py
│   ├── test_indexer.py
│   ├── test_graph_builder.py
│   └── test_api.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```
