# REPOEVOLUTION ⚡
### Software Evolution Intelligence Engine & Grounded Developer Copilot

RepoEvolution is an NLP-powered developer intelligence system that parses software repositories, builds Abstract Syntax Tree (AST) entity representations, maintains a dependency call-graph (`ChangeGraph`), computes AST semantic diffs (`SemanticDiff`), analyzes multi-commit historical patterns for architectural drift (`DriftGuard`), and provides an evidence-grounded AI Copilot for developer Q&A.

> **Key Architectural Insight:**
> *"RepoEvolution is not simply a chatbot over source code. It combines repository structure, semantic version comparison, historical pattern analysis, retrieval and evidence-grounded LLM explanations."*

---

## 🏗️ System Architecture

```
+-----------------------------------------------------------------------------------+
|                               REPOEVOLUTION ARCHITECTURE                          |
+-----------------------------------------------------------------------------------+
                                          |
  1. RepoSense Ingestion Layer            v
     +----------------------------------------------------------------------------+
     | Python AST Parser -> BM25 + FAISS Vector Index (RRF) -> NetworkX Graph     |
     +----------------------------------------------------------------------------+
                                          |
  2. Semantic Version Comparison Layer    v
     +----------------------------------------------------------------------------+
     | GitSnapshotLoader -> SemanticEntityDiffEngine (7 AST Semantic Types)       |
     +----------------------------------------------------------------------------+
                                          |
  3. Architectural DriftGuard Layer       v
     +----------------------------------------------------------------------------+
     | HistoryAnalyzer -> PatternExtractor -> DriftDetectionEngine                |
     +----------------------------------------------------------------------------+
                                          |
  4. Grounded Copilot Layer               v
     +----------------------------------------------------------------------------+
     | GeminiProvider / Evidence-Grounded Context -> Cited User Response          |
     +----------------------------------------------------------------------------+
```

---

## ⚡ Core Engine Components

1. **RepoSense AST Ingest Engine**: Native Python AST parsing via `BaseParser` abstraction for extracting classes, functions, methods, docstrings, and call dependencies.
2. **Hybrid Search Index**: Combines sparse keyword search (**BM25**) with dense semantic vector embeddings (**sentence-transformers/all-MiniLM-L6-v2** + **FAISS**) using Reciprocal Rank Fusion (RRF).
3. **ChangeGraph**: Directed dependency and call graph built using **NetworkX** to compute downstream impact propagation.
4. **SemanticDiff**: AST-aware Git commit comparison engine (`GitSnapshotLoader` + `SemanticEntityDiffEngine`) classifying changes into `ADDED`, `REMOVED`, `MODIFIED`, `RENAMED`, `SIGNATURE_CHANGED`, `DEPENDENCY_CHANGED`, and `DOCSTRING_CHANGED` without modifying working tree.
5. **DriftGuard**: Evidence-driven historical pattern drift engine (`HistoryAnalyzer` + `PatternExtractor` + `DriftDetectionEngine`) evaluating target commits against historical commit sequences for `DEPENDENCY_DRIFT`, `API_DRIFT`, and `STRUCTURAL_DRIFT`.
6. **Grounded Copilot**: RAG pipeline powered by **Gemini Provider** abstraction (`LLMProvider`) that forces answers to cite exact file lines (`[filepath#Lstart-Lend]`).
7. **REST API**: Asynchronous FastAPI endpoints (`/api/v1/repo/ingest`, `/api/v1/repo/search`, `/api/v1/repo/compare`, `/api/v1/repo/drift`, `/api/v1/graph/data`, `/api/v1/copilot/ask`).
8. **Streamlit UI**: Dark mode developer dashboard with interactive tabs (Overview, Search, Semantic Compare, DriftGuard, ChangeGraph, Copilot).

---

## 🔍 End-to-End Example Scenario

Consider a repository evolving across 4 commits:

- **Commit A**: `PaymentService.process_payment` calls `PaymentRepository`.
- **Commit B**: Added docstrings to `PaymentService`.
- **Commit C**: Added validation in `PaymentService` while maintaining `PaymentRepository` call.
- **Commit D**: `PaymentService` switches to call `DirectDatabaseClient` directly, bypassing the repository pattern.

### Pipeline Processing Execution:

```bash
# 1. Parse repository AST & Index
POST /api/v1/repo/ingest -> 2 files parsed, 7 entities indexed into BM25 + FAISS

# 2. Semantic Version Comparison (Commit C vs Commit D)
POST /api/v1/repo/compare -> Detects DEPENDENCY_CHANGED on PaymentService.process_payment

# 3. Architectural Drift Detection (History depth: 5)
POST /api/v1/repo/drift -> Detects DEPENDENCY_DRIFT (Confidence: 1.00) with evidence commits A, B, C

# 4. Grounded Copilot Explanation
POST /api/v1/copilot/ask -> Explains drift grounded in AST evidence blocks with line citations
```

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

### Option A: Launch via Docker Compose (Recommended for Production / Containerized Environments)
```bash
# Build and start both FastAPI backend and Streamlit frontend containers
docker compose up -d

# View service logs
docker compose logs -f

# Stop container services
docker compose down
```
* **Streamlit Interface**: `http://localhost:8501`
* **FastAPI Backend Service**: `http://localhost:8000`
* **Swagger API Docs**: `http://localhost:8000/docs`

### Option B: Launch Streamlit Developer Interface Locally
```bash
streamlit run ui/app.py
```
Open your browser at `http://localhost:8501`.

### Option C: Launch FastAPI Backend Server Locally
```bash
uvicorn src.api.main:app --reload --port 8000
```
* **Interactive API Documentation (Swagger)**: `http://localhost:8000/docs`
* **Alternative API Documentation (ReDoc)**: `http://localhost:8000/redoc`

---

## 🔒 Security Guidelines & Environment Configuration

> ⚠️ **CRITICAL SECURITY REQUIREMENT**:
> **Never commit `.env` or hardcode API credentials!** `.env` is listed in `.gitignore` and `.dockerignore`.
> Always configure secrets using environment variables or container runtime environment injections.

### Required Environment Variables:
| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *(None)* | Google Gemini API Key for grounded copilot LLM responses. |
| `DEFAULT_GEMINI_MODEL` | `gemini-2.5-flash` | Active Gemini model used for synthesis. |
| `PROJECT_NAME` | `RepoEvolution` | Project branding label. |
| `VERSION` | `1.0.0` | API engine version string. |

---

## 🌐 FastAPI Endpoint Directory

| Endpoint Method & Path | Summary & Function |
| :--- | :--- |
| `GET /health` | Health check endpoint returning system status. |
| `GET /` | Root endpoint returning API metadata. |
| `POST /api/v1/repo/ingest` | Ingests repository directory, parses Python AST, and builds vector index. |
| `POST /api/v1/repo/search` | Performs hybrid BM25 + FAISS RRF search across codebase. |
| `POST /api/v1/repo/compare` | Calculates AST semantic diffs between two Git commit revisions. |
| `POST /api/v1/repo/drift` | Evaluates target commit against multi-commit history for architectural drift. |
| `GET /api/v1/graph/data` | Retrieves dependency and call graph nodes and edges. |
| `POST /api/v1/copilot/ask` | Submits natural language queries to evidence-grounded Copilot. |

---

## 🚀 Production Deployment & Containerization Notes

* **Container Architecture**: Multi-stage lightweight Python container image built via `Dockerfile` with system dependencies (`git`, `curl`).
* **Service Networking**: `docker-compose.yml` isolates the FastAPI backend (`repoevolution-backend`) and Streamlit frontend (`repoevolution-frontend`) on an internal bridge network.
* **Secret Injection**: In production deployments (e.g. Kubernetes, AWS ECS, Docker Swarm), pass `GEMINI_API_KEY` via container secret management or environment variable injection:
  ```bash
  GEMINI_API_KEY="your_production_key" docker compose up -d
  ```

---

## 🧪 Running Automated Tests

Run the complete Pytest suite (including end-to-end integration tests):
```bash
# Windows:
.\.venv\Scripts\python.exe -m pytest tests/ -v
# Linux/macOS:
.venv/bin/pytest -v
```

---

## 📁 Repository Structure

```
RepoEvolution/
├── docs/                         # Architecture & Evaluation Reports
│   ├── prompt_evaluation.md      # Prompt Effectiveness Matrix
│   └── evaluation_report.md      # Phase 3.5 Integration & Benchmark Report
├── prompts/                      # Externalized Version-Controlled Prompts
│   ├── system_copilot.txt        # Grounded system prompt for Copilot
│   ├── prompt_semantic_diff.txt  # AST diff rationale prompt
│   ├── prompt_drift.txt          # Evolutionary drift prompt
│   └── driftguard_system.txt     # Multi-commit architectural drift prompt
├── scratch/
│   └── smoke_test_phase3_5.py    # Benchmark execution script
├── src/
│   ├── api/                      # FastAPI Router & Endpoints
│   ├── changegraph/              # NetworkX Call Graph Builder
│   ├── copilot/                  # Gemini LLM Provider & Evidence Retriever
│   ├── core/                     # Settings, Config, Pydantic Data Models
│   ├── driftguard/               # HistoryAnalyzer, PatternExtractor & DriftEngine
│   ├── reposense/                # AST Parser & FAISS+BM25 Hybrid Indexer
│   └── semantic_diff/            # GitSnapshotLoader & SemanticDiff Engine
├── tests/                        # Pytest Automated Test Suite
└── ui/                           # Streamlit Interactive Web Application
```
