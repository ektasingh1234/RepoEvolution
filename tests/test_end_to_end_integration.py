import pytest
from pathlib import Path
from git import Repo

from src.reposense.python_parser import PythonASTParser
from src.reposense.indexer import RepositoryIndexer
from src.changegraph.graph_builder import DependencyGraphBuilder
from src.semantic_diff.git_loader import GitSnapshotLoader
from src.semantic_diff.entity_diff import SemanticEntityDiffEngine
from src.semantic_diff.summary_builder import SemanticSummaryBuilder
from src.driftguard.history_analyzer import HistoryAnalyzer
from src.driftguard.pattern_extractor import PatternExtractor
from src.driftguard.drift_engine import DriftDetectionEngine
from src.copilot.llm_provider import GeminiProvider
from src.core.models import DriftType, SemanticChangeType


def test_end_to_end_pipeline_integration(tmp_path: Path):
    """
    End-to-End Integration Scenario:
    1. Create a controlled synthetic git repo with 4 commits:
       - Commit A: PaymentService -> PaymentRepository
       - Commit B: PaymentService -> PaymentRepository (minor updates)
       - Commit C: PaymentService -> PaymentRepository (pattern established)
       - Commit D: PaymentService -> DirectDatabaseClient (drift introduced!)
    2. Run RepoSense: AST parsing, entity extraction, hybrid indexing, graph building.
    3. Run SemanticDiff: compare Commit C (base) vs Commit D (target).
    4. Run DriftGuard: extract historical patterns from A, B, C, detect drift in D.
    5. Pass evidence to Grounded Copilot (GeminiProvider offline or online fallback).
    6. Verify evidence fields preserved across all pipeline stages.
    """
    # -------------------------------------------------------------------------
    # STEP 1: Create Controlled Synthetic Git Repository
    # -------------------------------------------------------------------------
    repo_dir = tmp_path / "integration_repo"
    repo_dir.mkdir()
    git_repo = Repo.init(repo_dir)
    git_repo.git.config("user.name", "Integration Tester")
    git_repo.git.config("user.email", "integration@example.com")

    payment_file = repo_dir / "payment_service.py"

    code_commit_a = """
class PaymentRepository:
    def save_transaction(self, tx_id: str, amount: float) -> bool:
        return True

class PaymentService:
    def process_payment(self, tx_id: str, amount: float) -> bool:
        repo = PaymentRepository()
        return repo.save_transaction(tx_id, amount)
"""

    code_commit_b = """
class PaymentRepository:
    def save_transaction(self, tx_id: str, amount: float) -> bool:
        \"\"\"Save transaction log to database.\"\"\"
        return True

class PaymentService:
    def process_payment(self, tx_id: str, amount: float) -> bool:
        \"\"\"Process payment via repository pattern.\"\"\"
        repo = PaymentRepository()
        return repo.save_transaction(tx_id, amount)
"""

    code_commit_c = """
class PaymentRepository:
    def save_transaction(self, tx_id: str, amount: float) -> bool:
        \"\"\"Save transaction log to database securely.\"\"\"
        return True

class PaymentService:
    def process_payment(self, tx_id: str, amount: float) -> bool:
        \"\"\"Process payment via repository pattern with validation.\"\"\"
        if amount <= 0:
            return False
        repo = PaymentRepository()
        return repo.save_transaction(tx_id, amount)
"""

    code_commit_d = """
class PaymentRepository:
    def save_transaction(self, tx_id: str, amount: float) -> bool:
        return True

class DirectDatabaseClient:
    def raw_insert(self, table: str, data: dict) -> bool:
        return True

class PaymentService:
    def process_payment(self, tx_id: str, amount: float) -> bool:
        \"\"\"Bypass repository layer and insert directly into DB.\"\"\"
        db = DirectDatabaseClient()
        return db.raw_insert("payments", {"id": tx_id, "amount": amount})
"""

    # Commit A
    payment_file.write_text(code_commit_a, encoding="utf-8")
    git_repo.index.add(["payment_service.py"])
    commit_a = git_repo.index.commit("Commit A: Initial PaymentService calling PaymentRepository")
    sha_a = commit_a.hexsha

    # Commit B
    payment_file.write_text(code_commit_b, encoding="utf-8")
    git_repo.index.add(["payment_service.py"])
    commit_b = git_repo.index.commit("Commit B: Add docstrings to PaymentService and PaymentRepository")
    sha_b = commit_b.hexsha

    # Commit C
    payment_file.write_text(code_commit_c, encoding="utf-8")
    git_repo.index.add(["payment_service.py"])
    commit_c = git_repo.index.commit("Commit C: Add validation in PaymentService")
    sha_c = commit_c.hexsha

    # Commit D
    payment_file.write_text(code_commit_d, encoding="utf-8")
    git_repo.index.add(["payment_service.py"])
    commit_d = git_repo.index.commit("Commit D: Bypass repository layer using DirectDatabaseClient")
    sha_d = commit_d.hexsha

    # -------------------------------------------------------------------------
    # STEP 2: RepoSense Pipeline Verification
    # -------------------------------------------------------------------------
    parser = PythonASTParser()
    parsed_entities = parser.parse_file(payment_file, repo_root=repo_dir)

    assert parsed_entities is not None
    assert len(parsed_entities) >= 3

    service_entity = next((e for e in parsed_entities if e.name == "PaymentService.process_payment"), None)
    assert service_entity is not None
    assert "DirectDatabaseClient" in service_entity.dependencies

    # Ingest into repository indexer
    indexer = RepositoryIndexer()
    total_files, total_entities = indexer.index_repository(repo_dir)
    assert total_files >= 1
    assert total_entities >= 3

    search_res = indexer.search("DirectDatabaseClient", top_k=2)
    assert len(search_res) > 0
    assert any("DirectDatabaseClient" in r.entity.code_content or r.entity.name == "DirectDatabaseClient" for r in search_res)

    # Dependency Graph
    graph_builder = DependencyGraphBuilder()
    graph = graph_builder.build_graph(parsed_entities)
    graph_data = graph_builder.get_graph_data()
    assert len(graph_data.nodes) >= 3

    # -------------------------------------------------------------------------
    # STEP 3: SemanticDiff Verification (Commit C vs Commit D)
    # -------------------------------------------------------------------------
    loader = GitSnapshotLoader(repo_dir)
    entities_c, _ = loader.parse_commit_snapshot(sha_c)
    entities_d, _ = loader.parse_commit_snapshot(sha_d)

    diff_engine = SemanticEntityDiffEngine()
    diffs = diff_engine.diff_entities(entities_c, entities_d)

    # Find process_payment diff
    proc_diff = next((d for d in diffs if "process_payment" in d.entity_name), None)
    assert proc_diff is not None
    assert proc_diff.change_type in (SemanticChangeType.DEPENDENCY_CHANGED, SemanticChangeType.MODIFIED)
    assert proc_diff.file_before == "payment_service.py"
    assert proc_diff.file_after == "payment_service.py"
    assert proc_diff.evidence is not None

    summary = SemanticSummaryBuilder.build_summary(diffs)
    assert len(summary.categorized_summaries) > 0

    # -------------------------------------------------------------------------
    # STEP 4: DriftGuard Verification (Commit A..C history vs Commit D)
    # -------------------------------------------------------------------------
    history_analyzer = HistoryAnalyzer(repo_dir)
    snapshots = history_analyzer.get_historical_snapshots(target_commit=sha_d, history_depth=5)
    patterns = PatternExtractor.extract_patterns(snapshots)

    drift_engine = DriftDetectionEngine(min_confidence=0.70)
    drift_findings = drift_engine.detect_drift(entities_d, patterns)

    assert len(drift_findings) >= 1
    dep_drift = next((f for f in drift_findings if f.drift_type == DriftType.DEPENDENCY_DRIFT), None)
    assert dep_drift is not None
    assert dep_drift.entity == "PaymentService.process_payment"
    assert "PaymentRepository" in dep_drift.historical_pattern
    assert dep_drift.confidence >= 0.75
    # Verify commit SHAs preserved in evidence
    assert any(sha_a[:8] in c or c == sha_a for c in dep_drift.evidence_commits)

    # -------------------------------------------------------------------------
    # STEP 5: Evidence Grounding & Copilot Verification
    # -------------------------------------------------------------------------
    provider = GeminiProvider()
    question = "Why was a DriftGuard warning generated for process_payment in commit D?"
    evidence_text = (
        f"SemanticDiff Evidence:\n"
        f"- Change: {proc_diff.change_type.value} on {proc_diff.entity_name}\n"
        f"- Evidence: {proc_diff.evidence}\n\n"
        f"DriftGuard Evidence:\n"
        f"- Drift Type: {dep_drift.drift_type.value}\n"
        f"- Entity: {dep_drift.entity}\n"
        f"- Historical Pattern: {dep_drift.historical_pattern}\n"
        f"- Current Pattern: {dep_drift.current_pattern}\n"
        f"- Evidence Commits: {dep_drift.evidence_commits}\n"
        f"- Confidence: {dep_drift.confidence}\n"
    )

    copilot_res = provider.generate_grounded_answer(
        question=question,
        retrieved_entities=[service_entity],
        evidence_summary=evidence_text
    )

    assert copilot_res is not None
    assert copilot_res.answer is not None
    assert len(copilot_res.answer) > 0
    assert copilot_res.model_used == "offline-evidence-retriever" or copilot_res.model_used.startswith("gemini-") or copilot_res.model_used == provider.active_model
    assert len(copilot_res.citations) >= 1

    # Cleanup Windows file locks cleanly
    loader.git_repo.close()
    history_analyzer.git_repo.close()
    git_repo.close()
