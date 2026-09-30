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
