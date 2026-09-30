from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from src.core.models import (
    IngestRequest, IngestSummary, SearchQuery, SearchResponse,
    CopilotRequest, CopilotResponse, GraphData
)
from src.reposense.indexer import RepositoryIndexer
from src.changegraph.graph_builder import DependencyGraphBuilder
from src.copilot.llm_provider import GeminiProvider

router = APIRouter(prefix="/api/v1", tags=["Repository Operations"])

# Global Singleton State for Phase 1 In-Memory Engine
global_indexer = RepositoryIndexer()
global_graph_builder = DependencyGraphBuilder()
global_llm_provider = GeminiProvider()
current_repo_path: Optional[str] = None


@router.post("/repo/ingest", response_model=IngestSummary)
def ingest_repository(payload: IngestRequest):
    global current_repo_path
    repo_dir = Path(payload.repo_path).resolve()
    if not repo_dir.exists() or not repo_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"Invalid repository path: {payload.repo_path}")

    try:
        total_files, total_entities = global_indexer.index_repository(repo_dir)
        global_graph_builder.build_graph(global_indexer.entities)
        current_repo_path = str(repo_dir)

        counts = {}
        for entity in global_indexer.entities:
            val = entity.entity_type.value
            counts[val] = counts.get(val, 0) + 1

        return IngestSummary(
            repo_path=current_repo_path,
            total_files_parsed=total_files,
            total_entities_extracted=total_entities,
            entity_counts=counts,
            status="success",
            message=f"Successfully ingested {total_files} files and extracted {total_entities} entities."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/repo/overview")
def get_overview():
    if not current_repo_path or not global_indexer.entities:
        return {
            "status": "uninitialized",
            "message": "No repository has been ingested yet.",
            "total_files": 0,
            "total_entities": 0,
            "entity_counts": {}
        }

    counts = {}
    for entity in global_indexer.entities:
        val = entity.entity_type.value
        counts[val] = counts.get(val, 0) + 1

    return {
        "status": "ready",
        "repo_path": current_repo_path,
        "total_entities": len(global_indexer.entities),
        "entity_counts": counts,
        "sample_entities": [e.name for e in global_indexer.entities[:10]]
    }


@router.post("/repo/search", response_model=SearchResponse)
def search_code(payload: SearchQuery):
    if not global_indexer.entities:
        raise HTTPException(status_code=400, detail="Repository not ingested yet.")

    results = global_indexer.search(query=payload.query, top_k=payload.top_k)
    return SearchResponse(
        query=payload.query,
        total_results=len(results),
        results=results
    )


@router.get("/graph/data", response_model=GraphData)
def get_graph_data():
    return global_graph_builder.get_graph_data()


@router.post("/copilot/ask", response_model=CopilotResponse)
def ask_copilot(payload: CopilotRequest):
    if not global_indexer.entities:
        raise HTTPException(status_code=400, detail="Repository must be ingested before asking Copilot.")

    # 1. Retrieve top_k relevant entities using hybrid index
    search_results = global_indexer.search(query=payload.question, top_k=payload.top_k)
    retrieved_entities = [r.entity for r in search_results]

    # 2. Build evidence summary context string
    evidence_lines = []
    for r in search_results:
        e = r.entity
        evidence_lines.append(
            f"--- ENTITY: {e.id} ({e.entity_type.value}) ---\n"
            f"File: {e.file_path} (Lines {e.start_line}-{e.end_line})\n"
            f"Signature: {e.signature}\n"
            f"Docstring: {e.docstring or 'None'}\n"
            f"Dependencies: {', '.join(e.dependencies) if e.dependencies else 'None'}\n"
            f"Code Content:\n{e.code_content}\n"
        )

    evidence_summary = "\n".join(evidence_lines)

    # 3. Generate grounded answer from LLM provider
    response = global_llm_provider.generate_grounded_answer(
        question=payload.question,
        retrieved_entities=retrieved_entities,
        evidence_summary=evidence_summary
    )
    return response
