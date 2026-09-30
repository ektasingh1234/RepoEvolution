import sys
import pathlib
import tempfile
from git import Repo

sys.path.insert(0, str(pathlib.Path(".").resolve()))

from src.driftguard.history_analyzer import HistoryAnalyzer
from src.driftguard.pattern_extractor import PatternExtractor
from src.driftguard.drift_engine import DriftDetectionEngine
from src.semantic_diff.git_loader import GitSnapshotLoader
from src.core.models import DriftType

print("=== PHASE 3 SMOKE TEST: DRIFTGUARD HISTORICAL PATTERN ANALYSIS ===")

with tempfile.TemporaryDirectory() as tmp_dir:
    repo_dir = pathlib.Path(tmp_dir) / "synthetic_drift_repo"
    repo_dir.mkdir()

    repo = Repo.init(repo_dir)
    repo.git.config("user.name", "Drift Bot")
    repo.git.config("user.email", "drift@example.com")

    # Historical Commits 1..3 establishing PaymentService -> PaymentRepository
    code_history = """
def process_payment(amount: float) -> bool:
    \"\"\"Process payment using PaymentRepository.\"\"\"
    repo = PaymentRepository()
    return repo.save(amount)

class PaymentRepository:
    def save(self, amount: float) -> bool:
        return True
"""
    file_p = repo_dir / "payment_service.py"
    for i in range(1, 4):
        file_p.write_text(code_history + f"\n# Commit {i}\n", encoding="utf-8")
        repo.index.add(["payment_service.py"])
        repo.index.commit(f"Commit {i}: Establish PaymentRepository pattern")

    # Target Commit 4: PaymentService switches dependency to DirectDatabaseClient (DEPENDENCY_DRIFT!)
    code_drifted = """
def process_payment(amount: float) -> bool:
    \"\"\"Process payment directly via database client.\"\"\"
    client = DirectDatabaseClient()
    return client.query(amount)

class PaymentRepository:
    def save(self, amount: float) -> bool:
        return True

class DirectDatabaseClient:
    def query(self, amount: float) -> bool:
        return True
"""
    file_p.write_text(code_drifted, encoding="utf-8")
    repo.index.add(["payment_service.py"])
    commit4 = repo.index.commit("Commit 4: Switch to DirectDatabaseClient")
    target_sha = commit4.hexsha

    print(f"Target Commit SHA: {target_sha[:8]}")

    analyzer = HistoryAnalyzer(repo_dir)
    snapshots = analyzer.get_historical_snapshots(target_commit=target_sha, history_depth=5)
    patterns = PatternExtractor.extract_patterns(snapshots)
    print(f"Historical Snapshots Analyzed: {len(snapshots)}")
    print(f"Learned Historical Patterns Count: {len(patterns)}")

    loader = GitSnapshotLoader(repo_dir)
    target_entities, _ = loader.parse_commit_snapshot(target_sha)

    engine = DriftDetectionEngine(min_confidence=0.70)
    findings = engine.detect_drift(target_entities, patterns)

    print(f"\nDrift Findings Count: {len(findings)}")
    assert len(findings) >= 1, "Expected at least 1 drift finding"

    for idx, f in enumerate(findings, 1):
        print(f"  #{idx} [{f.drift_type.value}] ({f.severity.value}) Entity: '{f.entity}'")
        print(f"     Historical Pattern: {f.historical_pattern}")
        print(f"     Current Pattern:    {f.current_pattern}")
        print(f"     Confidence:         {f.confidence:.2f}")
        print(f"     Recommendation:     {f.recommendation_basis}")

    loader.git_repo.close()
    analyzer.git_repo.close()
    repo.close()

    print("\n[SUCCESS] PHASE 3 DRIFTGUARD SMOKE TEST PASSED PERFECTLY!")
