import pytest
from pathlib import Path
from git import Repo
from fastapi.testclient import TestClient

from src.core.models import DriftType, DriftSeverity, DriftRequest
from src.driftguard.history_analyzer import HistoryAnalyzer
from src.driftguard.pattern_extractor import PatternExtractor
from src.driftguard.drift_engine import DriftDetectionEngine
from src.semantic_diff.git_loader import GitSnapshotLoader
from src.api.main import app

client = TestClient(app)


def test_driftguard_synthetic_drift_and_insufficient_history_cases(tmp_path: Path):
    """
    Integration test creating 2 synthetic repositories:
    1. repo_drift: 4 historical commits establishing PaymentService -> PaymentRepository (confidence 1.0).
       Commit 5 switches PaymentService -> DatabaseClient (DEPENDENCY_DRIFT detected).
    2. repo_no_drift: Only 1 single commit or low historical consistency.
       Commit 2 modifies calls, but confidence is < min_confidence (NO drift detected).
    """
    # =========================================================================
    # REPOSITORY 1: HIGH CONFIDENCE DEPENDENCY DRIFT (SHOULD DETECT DRIFT)
    # =========================================================================
    repo_dir1 = tmp_path / "repo_drift"
    repo_dir1.mkdir()
    repo1 = Repo.init(repo_dir1)
    repo1.git.config("user.name", "Test Bot")
    repo1.git.config("user.email", "bot@example.com")

    # Commits 1..4: PaymentService consistently calls PaymentRepository
    code_historical = """
def process_payment(amount: float) -> bool:
    \"\"\"Process payment via repository.\"\"\"
    repo = PaymentRepository()
    return repo.save(amount)

class PaymentRepository:
    def save(self, amount: float) -> bool:
        return True
"""

    file1 = repo_dir1 / "payment.py"
    for i in range(1, 5):
        file1.write_text(code_historical + f"\n# Commit {i}\n", encoding="utf-8")
        repo1.index.add(["payment.py"])
        repo1.index.commit(f"Commit {i}: Maintain PaymentRepository call")

    # Commit 5 (Target): PaymentService switches to DatabaseClient (DEPENDENCY_DRIFT!)
    code_drifted = """
def process_payment(amount: float) -> bool:
    \"\"\"Process payment via database client directly.\"\"\"
    client = DatabaseClient()
    return client.execute(amount)

class PaymentRepository:
    def save(self, amount: float) -> bool:
        return True

class DatabaseClient:
    def execute(self, amount: float) -> bool:
        return True
"""
    file1.write_text(code_drifted, encoding="utf-8")
    repo1.index.add(["payment.py"])
    commit5 = repo1.index.commit("Commit 5: Switch to DatabaseClient directly")
    sha5 = commit5.hexsha

    # Evaluate Repo 1
    analyzer1 = HistoryAnalyzer(repo_dir1)
    snapshots1 = analyzer1.get_historical_snapshots(target_commit=sha5, history_depth=5)
    patterns1 = PatternExtractor.extract_patterns(snapshots1)

    loader1 = GitSnapshotLoader(repo_dir1)
    target_entities1, _ = loader1.parse_commit_snapshot(sha5)

    engine1 = DriftDetectionEngine(min_confidence=0.70)
    findings1 = engine1.detect_drift(target_entities1, patterns1)

    assert len(findings1) >= 1, "Failed to detect DEPENDENCY_DRIFT in Repo 1"
    dep_finding = next(f for f in findings1 if f.drift_type == DriftType.DEPENDENCY_DRIFT)
    assert dep_finding.entity == "process_payment"
    assert "PaymentRepository" in dep_finding.historical_pattern
    assert dep_finding.confidence >= 0.75

    loader1.git_repo.close()
    repo1.close()

    # =========================================================================
    # REPOSITORY 2: INSUFFICIENT HISTORY (SHOULD NOT DETECT DRIFT)
    # =========================================================================
    repo_dir2 = tmp_path / "repo_no_drift"
    repo_dir2.mkdir()
    repo2 = Repo.init(repo_dir2)
    repo2.git.config("user.name", "Test Bot")
    repo2.git.config("user.email", "bot@example.com")

    # Commit 1: Only 1 commit (insufficient historical depth for high confidence)
    file2 = repo_dir2 / "service.py"
    file2.write_text("def do_work(): old_helper()\ndef old_helper(): pass\n", encoding="utf-8")
    repo2.index.add(["service.py"])
    repo2.index.commit("Commit 1: Initial commit")

    # Commit 2 (Target): Switched to new_helper
    file2.write_text("def do_work(): new_helper()\ndef new_helper(): pass\n", encoding="utf-8")
    repo2.index.add(["service.py"])
    commit_target2 = repo2.index.commit("Commit 2: Switch helper")
    sha_target2 = commit_target2.hexsha

    # Evaluate Repo 2 with high min_confidence threshold (0.80)
    analyzer2 = HistoryAnalyzer(repo_dir2)
    snapshots2 = analyzer2.get_historical_snapshots(target_commit=sha_target2, history_depth=5)
    patterns2 = PatternExtractor.extract_patterns(snapshots2)

    loader2 = GitSnapshotLoader(repo_dir2)
    target_entities2, _ = loader2.parse_commit_snapshot(sha_target2)

    engine2 = DriftDetectionEngine(min_confidence=0.80)
    findings2 = engine2.detect_drift(target_entities2, patterns2)

    # NO drift should be claimed because historical confidence is insufficient
    assert len(findings2) == 0, f"Expected 0 drift findings for insufficient history, got {len(findings2)}"

    loader2.git_repo.close()
    repo2.close()


def test_driftguard_api_endpoint(tmp_path: Path):
    """Test POST /api/v1/repo/drift endpoint."""
    repo_dir = tmp_path / "api_test_repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    repo.git.config("user.name", "Test Bot")
    repo.git.config("user.email", "bot@example.com")

    file_p = repo_dir / "api.py"
    file_p.write_text("def fetch_user(user_id: int):\n    return {}\n", encoding="utf-8")
    repo.index.add(["api.py"])
    c1 = repo.index.commit("C1")

    file_p.write_text("def fetch_user(user_id: int):\n    return {}\n# c2\n", encoding="utf-8")
    repo.index.add(["api.py"])
    c2 = repo.index.commit("C2")

    # C3: API Signature Change (API_DRIFT)
    file_p.write_text("def fetch_user(user_id: int, auth_token: str):\n    return {}\n", encoding="utf-8")
    repo.index.add(["api.py"])
    c3 = repo.index.commit("C3: Change signature")

    response = client.post(
        "/api/v1/repo/drift",
        json={
            "repo_path": str(repo_dir),
            "target_commit": c3.hexsha,
            "history_depth": 3,
            "min_confidence": 0.60,
            "include_explanation": True
        }
    )

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["total_findings"] >= 1
    api_finding = next(f for f in res_json["findings"] if f["drift_type"] == "API_DRIFT")
    assert api_finding["entity"] == "fetch_user"

    loader = GitSnapshotLoader(repo_dir)
    loader.git_repo.close()
    repo.close()
