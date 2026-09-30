import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import os
import tempfile
from git import Repo
import pytest

from src.core.config import settings
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


def run_phase_3_5_audit():
    print("=================================================================")
    print("REPOEVOLUTION PHASE 3.5: INTEGRATION & EVALUATION AUDIT SMOKE TEST")
    print("=================================================================\n")

    # 1. API Key Verification
    gemini_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key.strip():
        print("[API STATUS] GEMINI_API_KEY configured. Real LLM API verification active.")
        real_api_available = True
    else:
        print("[API STATUS] GEMINI_API_KEY is unconfigured. Deterministic offline evidence fallback active.")
        real_api_available = False

    # 2. Setup Controlled Synthetic Test Repo
    print("\n--- 1. Setting up 4-Commit Synthetic Test Repository ---")
    tmp_dir = tempfile.TemporaryDirectory()
    repo_dir = Path(tmp_dir.name)
    git_repo = Repo.init(repo_dir)
    git_repo.git.config("user.name", "Audit Bot")
    git_repo.git.config("user.email", "audit@example.com")

    auth_file = repo_dir / "auth.py"
    payment_file = repo_dir / "payment_service.py"

    auth_code = """
def authenticate_user(token: str) -> bool:
    \"\"\"Authenticate user token.\"\"\"
    return token == "valid_token"
"""
    auth_file.write_text(auth_code, encoding="utf-8")

    c1_code = """
class PaymentRepository:
    def save(self, amount: float) -> bool:
        return True

class PaymentService:
    def process(self, amount: float) -> bool:
        repo = PaymentRepository()
        return repo.save(amount)
"""
    c2_code = """
class PaymentRepository:
    def save(self, amount: float) -> bool:
        \"\"\"Save payment.\"\"\"
        return True

class PaymentService:
    def process(self, amount: float) -> bool:
        \"\"\"Process payment using repository pattern.\"\"\"
        repo = PaymentRepository()
        return repo.save(amount)
"""
    c3_code = """
class PaymentRepository:
    def save(self, amount: float) -> bool:
        \"\"\"Save payment record.\"\"\"
        return True

class PaymentService:
    def process(self, amount: float) -> bool:
        \"\"\"Process payment with validation using repository pattern.\"\"\"
        if amount <= 0: return False
        repo = PaymentRepository()
        return repo.save(amount)
"""
    c4_code = """
class PaymentRepository:
    def save(self, amount: float) -> bool:
        return True

class DirectDatabaseClient:
    def raw_insert(self, data: dict) -> bool:
        return True

class PaymentService:
    def process(self, amount: float) -> bool:
        \"\"\"Bypass repository layer and insert directly into DB.\"\"\"
        db = DirectDatabaseClient()
        return db.raw_insert({"amount": amount})
"""

    payment_file.write_text(c1_code, encoding="utf-8")
    git_repo.index.add(["auth.py", "payment_service.py"])
    commit1 = git_repo.index.commit("Commit 1: Initial PaymentService calling PaymentRepository")

    payment_file.write_text(c2_code, encoding="utf-8")
    git_repo.index.add(["payment_service.py"])
    commit2 = git_repo.index.commit("Commit 2: Add docstrings")

    payment_file.write_text(c3_code, encoding="utf-8")
    git_repo.index.add(["payment_service.py"])
    commit3 = git_repo.index.commit("Commit 3: Add input validation")

    payment_file.write_text(c4_code, encoding="utf-8")
    git_repo.index.add(["payment_service.py"])
    commit4 = git_repo.index.commit("Commit 4: Drift - call DirectDatabaseClient directly")

    sha1, sha2, sha3, sha4 = commit1.hexsha, commit2.hexsha, commit3.hexsha, commit4.hexsha

    # 3. Measure Ingestion & Parser Latency
    print("\n--- 2. Measuring Ingestion & Hybrid Search Performance ---")
    t0 = time.perf_counter()
    indexer = RepositoryIndexer()
    total_files, total_entities = indexer.index_repository(repo_dir)
    t_ingest = (time.perf_counter() - t0) * 1000
    print(f"Ingestion Latency: {t_ingest:.2f} ms ({total_files} files, {total_entities} entities)")

    # Benchmark Queries for Retrieval Hit-Rate
    benchmark_queries = [
        ("Where is authentication implemented?", "auth.py", "authenticate_user"),
        ("Which function calls PaymentRepository?", "payment_service.py", "PaymentService.process"),
        ("Where is DirectDatabaseClient used?", "payment_service.py", "DirectDatabaseClient"),
        ("What handles saving transactions?", "payment_service.py", "PaymentRepository"),
        ("What validates amount?", "payment_service.py", "PaymentService.process"),
    ]

    hits = 0
    t_search_total = 0.0
    for q, exp_file, exp_entity in benchmark_queries:
        ts0 = time.perf_counter()
        res = indexer.search(q, top_k=3)
        ts_elapsed = (time.perf_counter() - ts0) * 1000
        t_search_total += ts_elapsed

        hit = any(r.entity.file_path.endswith(exp_file) and exp_entity in r.entity.name for r in res)
        if hit:
            hits += 1
        print(f"Query: '{q}' -> Top Hit: {[r.entity.name for r in res[:1]]} (Hit: {hit}, Latency: {ts_elapsed:.2f}ms)")

    hit_rate = (hits / len(benchmark_queries)) * 100
    avg_search_lat = t_search_total / len(benchmark_queries)
    print(f"Retrieval Benchmark: {hits}/{len(benchmark_queries)} Hits ({hit_rate:.1f}%), Avg Latency: {avg_search_lat:.2f} ms")

    # 4. SemanticDiff Evaluation
    print("\n--- 3. Measuring & Evaluating SemanticDiff ---")
    t0 = time.perf_counter()
    loader = GitSnapshotLoader(repo_dir)
    entities3, _ = loader.parse_commit_snapshot(sha3)
    entities4, _ = loader.parse_commit_snapshot(sha4)
    diff_engine = SemanticEntityDiffEngine()
    diffs = diff_engine.diff_entities(entities3, entities4)
    t_diff = (time.perf_counter() - t0) * 1000

    print(f"SemanticDiff Latency: {t_diff:.2f} ms")
    print(f"Detected Diffs ({len(diffs)}):")
    for d in diffs:
        print(f"  - [{d.change_type.value}] {d.entity_name} (Evidence: {d.evidence})")

    # 5. DriftGuard Evaluation
    print("\n--- 4. Measuring & Evaluating DriftGuard ---")
    t0 = time.perf_counter()
    analyzer = HistoryAnalyzer(repo_dir)
    snapshots = analyzer.get_historical_snapshots(target_commit=sha4, history_depth=5)
    patterns = PatternExtractor.extract_patterns(snapshots)
    drift_engine = DriftDetectionEngine(min_confidence=0.70)
    findings = drift_engine.detect_drift(entities4, patterns)
    t_drift = (time.perf_counter() - t0) * 1000

    print(f"DriftGuard Latency: {t_drift:.2f} ms")
    print(f"Detected Drift Findings ({len(findings)}):")
    for f in findings:
        print(f"  - [{f.drift_type.value}] {f.entity}: {f.description} (Confidence: {f.confidence:.2f})")

    # 6. Copilot Evidence Grounding Evaluation
    print("\n--- 5. Grounded Copilot Evaluation ---")
    t0 = time.perf_counter()
    provider = GeminiProvider()
    question = "Why did PaymentService drift from historical conventions in commit 4?"

    search_res = indexer.search(question, top_k=2)
    evidence_text = (
        f"SemanticDiff Evidence:\n"
        f"- Change Types: {[d.change_type.value for d in diffs]}\n"
        f"DriftGuard Evidence:\n"
        f"- Findings: {[{'type': f.drift_type.value, 'entity': f.entity, 'confidence': f.confidence} for f in findings]}\n"
    )

    copilot_res = provider.generate_grounded_answer(
        question=question,
        retrieved_entities=[r.entity for r in search_res],
        evidence_summary=evidence_text
    )
    t_copilot = (time.perf_counter() - t0) * 1000

    print(f"Copilot Latency: {t_copilot:.2f} ms")
    print(f"Model Used: {copilot_res.model_used}")
    print(f"Answer Preview:\n{copilot_res.answer[:300]}...")
    print(f"Citations Provided: {len(copilot_res.citations)}")

    # Cleanup Windows file locks
    loader.git_repo.close()
    analyzer.git_repo.close()
    git_repo.close()
    tmp_dir.cleanup()

    # 7. Summary Table Print
    print("\n=================================================================")
    print("PHASE 3.5 EVALUATION AUDIT SUMMARY")
    print("=================================================================")
    print(f"Ingestion Latency   : {t_ingest:.2f} ms")
    print(f"Hybrid Search Latency: {avg_search_lat:.2f} ms")
    print(f"SemanticDiff Latency: {t_diff:.2f} ms")
    print(f"DriftGuard Latency  : {t_drift:.2f} ms")
    print(f"Copilot Latency     : {t_copilot:.2f} ms")
    print(f"Retrieval Hit-Rate  : {hit_rate:.1f}% ({hits}/{len(benchmark_queries)})")
    print(f"Real Gemini API Status: {'ACTIVE' if real_api_available else 'UNCONFIGURED (Offline Evidence Fallback verified)'}")
    print("=================================================================\n")

if __name__ == "__main__":
    run_phase_3_5_audit()
