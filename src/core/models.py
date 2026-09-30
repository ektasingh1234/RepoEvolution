from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    IMPORT = "import"


class CodeEntity(BaseModel):
    id: str = Field(..., description="Unique entity identifier (filepath::entity_name)")
    name: str = Field(..., description="Entity name (function, class, or module name)")
    entity_type: EntityType
    file_path: str = Field(..., description="Relative file path within repository")
    start_line: int
    end_line: int
    signature: str = Field(..., description="Function/class signature string")
    docstring: Optional[str] = Field(None, description="Associated docstring if present")
    code_content: str = Field(..., description="Full source code snippet of entity")
    content_hash: str = Field(..., description="MD5/SHA256 hash of entity code content")
    dependencies: List[str] = Field(default_factory=list, description="IDs or names of referenced entities/imports")
    decorators: List[str] = Field(default_factory=list, description="List of decorators if any")


class IngestRequest(BaseModel):
    repo_path: str = Field(..., description="Absolute or relative path to target repository")
    force_reindex: bool = Field(False, description="Whether to rebuild index from scratch")


class IngestSummary(BaseModel):
    repo_path: str
    total_files_parsed: int
    total_entities_extracted: int
    entity_counts: Dict[str, int]
    status: str = "success"
    message: str = "Ingestion completed successfully."


class SearchQuery(BaseModel):
    query: str = Field(..., description="Natural language search query or symbol name")
    top_k: int = Field(5, description="Number of results to return")
    entity_type_filter: Optional[EntityType] = None


class SearchResult(BaseModel):
    entity: CodeEntity
    score: float
    retrieval_type: str = Field("hybrid", description="dense, sparse, or hybrid")


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResult]


class Citation(BaseModel):
    source_type: str = Field("file", description="file, commit, or entity")
    reference: str = Field(..., description="Markdown reference string e.g. path/to/file.py#L10-L25")
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    snippet: Optional[str] = None


class CopilotRequest(BaseModel):
    question: str = Field(..., description="User query about the codebase")
    top_k: int = Field(5, description="Number of context entities to retrieve")
    commit_sha: Optional[str] = None


class CopilotResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    retrieved_entities: List[CodeEntity] = Field(default_factory=list)
    model_used: str
    groundedness_score: float = Field(1.0, description="Estimated citation confidence score (0.0 to 1.0)")


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    file_path: str


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str = "calls"


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
