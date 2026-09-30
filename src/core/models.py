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


class SemanticChangeType(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    RENAMED = "RENAMED"
    SIGNATURE_CHANGED = "SIGNATURE_CHANGED"
    DEPENDENCY_CHANGED = "DEPENDENCY_CHANGED"
    DOCSTRING_CHANGED = "DOCSTRING_CHANGED"


class SemanticEntityDiff(BaseModel):
    change_id: str = Field(..., description="Unique identifier for this entity change")
    entity_type: EntityType
    entity_name: str
    file_before: Optional[str] = Field(None, description="File path in base commit")
    file_after: Optional[str] = Field(None, description="File path in target commit")
    change_type: SemanticChangeType
    similarity_score: float = Field(1.0, description="Cosine/Levenshtein similarity score (0.0 to 1.0)")
    before_summary: Optional[str] = Field(None, description="Signature or snippet in base commit")
    after_summary: Optional[str] = Field(None, description="Signature or snippet in target commit")
    affected_dependencies: List[str] = Field(default_factory=list, description="Dependencies changed or affected")
    evidence: str = Field(..., description="Concrete explanation of what changed in AST node")


class SemanticDiffSummary(BaseModel):
    total_added: int = 0
    total_removed: int = 0
    total_modified: int = 0
    total_signature_changed: int = 0
    total_renamed: int = 0
    total_dependency_changed: int = 0
    categorized_summaries: List[str] = Field(default_factory=list, description="Evidence-grounded high-level summary statements")


class CompareRequest(BaseModel):
    repo_path: Optional[str] = Field(None, description="Repository directory path (defaults to ingested repo)")
    base_commit: str = Field(..., description="Base Git commit SHA or branch/tag name (e.g. HEAD~1, main, sha1)")
    target_commit: str = Field(..., description="Target Git commit SHA or branch/tag name (e.g. HEAD, feature, sha2)")
    top_k: int = Field(10, description="Max diff items to return")
    include_explanation: bool = Field(True, description="Whether to include LLM-generated explanation")


class CompareResponse(BaseModel):
    base_commit: str
    target_commit: str
    summary: SemanticDiffSummary
    entity_diffs: List[SemanticEntityDiff]
    llm_explanation: Optional[str] = None
    model_used: Optional[str] = None


# Phase 3: DriftGuard Schemas
class DriftType(str, Enum):
    DEPENDENCY_DRIFT = "DEPENDENCY_DRIFT"
    API_DRIFT = "API_DRIFT"
    STRUCTURAL_DRIFT = "STRUCTURAL_DRIFT"


class DriftSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DriftFinding(BaseModel):
    drift_id: str
    drift_type: DriftType
    severity: DriftSeverity
    entity: str = Field(..., description="Entity name or ID where drift was detected")
    description: str = Field(..., description="Summary explanation of the drift finding")
    historical_pattern: str = Field(..., description="Established pattern across historical commits")
    current_pattern: str = Field(..., description="Current implementation pattern in target commit")
    evidence_commits: List[str] = Field(default_factory=list, description="SHAs of supporting historical commits")
    evidence_entities: List[str] = Field(default_factory=list, description="Historical entity IDs providing evidence")
    confidence: float = Field(..., description="Confidence score based on historical frequency (0.0 to 1.0)")
    recommendation_basis: str = Field(..., description="Evidence-grounded developer review recommendation")


class DriftRequest(BaseModel):
    repo_path: Optional[str] = Field(None, description="Repository directory path")
    target_commit: str = Field("HEAD", description="Target Git commit/revision to evaluate for drift")
    history_depth: int = Field(5, description="Number of historical commits to inspect")
    min_confidence: float = Field(0.70, description="Minimum pattern confidence threshold (0.0 to 1.0)")
    include_explanation: bool = Field(True, description="Whether to generate LLM explanation")


class DriftResponse(BaseModel):
    repo_path: str
    target_commit: str
    findings: List[DriftFinding]
    total_findings: int
    llm_explanation: Optional[str] = None
    model_used: Optional[str] = None


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
