import os
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from rank_bm25 import BM25Okapi

from src.core.config import settings
from src.core.models import CodeEntity, SearchResult
from src.reposense.base_parser import BaseParser
from src.reposense.python_parser import PythonASTParser

from src.core.logging_config import get_logger

logger = get_logger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    HAVE_VECTOR_SEARCH = True
except ImportError:
    HAVE_VECTOR_SEARCH = False


class RepositoryIndexer:
    """
    Scans repository, extracts entities using BaseParser implementations,
    and maintains BM25 + Vector embeddings hybrid search index.
    """

    def __init__(self, parsers: Optional[List[BaseParser]] = None):
        self.parsers: List[BaseParser] = parsers or [PythonASTParser()]
        self.entities: List[CodeEntity] = []
        self.entity_map: Dict[str, CodeEntity] = {}
        self.bm25: Optional[BM25Okapi] = None
        self.corpus_tokens: List[List[str]] = []
        
        # Dense Embedding Attributes
        self.embed_model = None
        self.faiss_index = None
        self.embedding_dimension = 384  # default for all-MiniLM-L6-v2

        if HAVE_VECTOR_SEARCH:
            try:
                self.embed_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
                if hasattr(self.embed_model, "get_embedding_dimension"):
                    self.embedding_dimension = self.embed_model.get_embedding_dimension()
                else:
                    self.embedding_dimension = self.embed_model.get_sentence_embedding_dimension()
            except Exception as e:
                logger.warning(f"Failed to load SentenceTransformer: {e}")

    def _tokenize(self, text: str) -> List[str]:
        """Simple code-friendly tokenizer splitting on non-alphanumeric chars."""
        import re
        return [t.lower() for t in re.split(r"[^\w]+", text) if len(t) > 1]

    def _entity_to_text(self, entity: CodeEntity) -> str:
        """Format CodeEntity into a text representation for embedding/indexing."""
        doc = entity.docstring or ""
        deps = " ".join(entity.dependencies)
        decs = " ".join(entity.decorators)
        return (
            f"File: {entity.file_path}\n"
            f"Name: {entity.name} Type: {entity.entity_type.value}\n"
            f"Signature: {entity.signature}\n"
            f"Decorators: {decs}\n"
            f"Dependencies: {deps}\n"
            f"Docstring: {doc}\n"
            f"Code:\n{entity.code_content}"
        )

    def index_repository(self, repo_path: str | Path) -> Tuple[int, int]:
        """
        Scan directory recursively, parse all supported files, and construct search index.
        Returns tuple: (total_files_parsed, total_entities_extracted)
        """
        repo_dir = Path(repo_path).resolve()
        if not repo_dir.exists() or not repo_dir.is_dir():
            raise ValueError(f"Repository directory does not exist: {repo_path}")

        self.entities.clear()
        self.entity_map.clear()

        total_files = 0
        for root, dirs, files in os.walk(repo_dir):
            # Skip hidden dirs, virtualenvs, __pycache__
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "venv", "env", "node_modules", "data")]
            for file in files:
                file_path = Path(root) / file
                for parser in self.parsers:
                    if parser.can_parse(file_path):
                        extracted = parser.parse_file(file_path, repo_root=repo_dir)
                        if extracted:
                            total_files += 1
                            for entity in extracted:
                                self.entities.append(entity)
                                self.entity_map[entity.id] = entity
                        break

        self._build_bm25_index()
        self._build_vector_index()
        return total_files, len(self.entities)

    def _build_bm25_index(self):
        """Construct BM25 sparse keyword index."""
        if not self.entities:
            self.bm25 = None
            self.corpus_tokens = []
            return

        self.corpus_tokens = [self._tokenize(self._entity_to_text(e)) for e in self.entities]
        self.bm25 = BM25Okapi(self.corpus_tokens)

    def _build_vector_index(self):
        """Construct FAISS dense vector embedding index."""
        if not HAVE_VECTOR_SEARCH or not self.embed_model or not self.entities:
            self.faiss_index = None
            return

        texts = [self._entity_to_text(e) for e in self.entities]
        embeddings = self.embed_model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

        embeddings_np = np.array(embeddings, dtype=np.float32)
        self.faiss_index = faiss.IndexFlatIP(self.embedding_dimension)
        self.faiss_index.add(embeddings_np)

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Execute Hybrid Search using Reciprocal Rank Fusion (RRF) between BM25 and Dense FAISS.
        """
        if not self.entities:
            return []

        top_k = min(top_k, len(self.entities))
        bm25_ranks: Dict[str, int] = {}
        faiss_ranks: Dict[str, int] = {}

        # 1. Sparse BM25 Search
        if self.bm25:
            query_tokens = self._tokenize(query)
            bm25_scores = self.bm25.get_scores(query_tokens)
            sorted_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
            for rank, idx in enumerate(sorted_indices[:top_k * 2]):
                bm25_ranks[self.entities[idx].id] = rank + 1

        # 2. Dense Vector Search
        if HAVE_VECTOR_SEARCH and self.embed_model and self.faiss_index:
            query_vector = self.embed_model.encode([query], normalize_embeddings=True)
            query_np = np.array(query_vector, dtype=np.float32)
            distances, indices = self.faiss_index.search(query_np, top_k * 2)
            for rank, idx in enumerate(indices[0]):
                if 0 <= idx < len(self.entities):
                    faiss_ranks[self.entities[idx].id] = rank + 1

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}
        rrf_constant = 60.0

        all_ids = set(bm25_ranks.keys()).union(set(faiss_ranks.keys()))
        if not all_ids:
            # Fallback if both empty: return first top_k
            return [SearchResult(entity=e, score=0.5, retrieval_type="fallback") for e in self.entities[:top_k]]

        for entity_id in all_ids:
            score = 0.0
            if entity_id in bm25_ranks:
                score += 1.0 / (rrf_constant + bm25_ranks[entity_id])
            if entity_id in faiss_ranks:
                score += 1.0 / (rrf_constant + faiss_ranks[entity_id])
            rrf_scores[entity_id] = score

        sorted_by_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results: List[SearchResult] = []
        for entity_id, rrf_score in sorted_by_rrf:
            entity = self.entity_map[entity_id]
            retrieval_type = "hybrid"
            if entity_id in bm25_ranks and entity_id not in faiss_ranks:
                retrieval_type = "sparse_bm25"
            elif entity_id in faiss_ranks and entity_id not in bm25_ranks:
                retrieval_type = "dense_vector"
            results.append(SearchResult(entity=entity, score=round(rrf_score, 4), retrieval_type=retrieval_type))

        return results
