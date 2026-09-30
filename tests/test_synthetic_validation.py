import pytest
from pathlib import Path
from git import Repo
from src.semantic_diff.git_loader import GitSnapshotLoader
from src.semantic_diff.entity_diff import SemanticEntityDiffEngine
from src.semantic_diff.summary_builder import SemanticSummaryBuilder
from src.core.models import SemanticChangeType


def test_synthetic_3_commit_validation(tmp_path: Path):
    """
    Validation Test over a dedicated synthetic Git repository with 3 distinct commits (A, B, C).
    Verifies detection of ADDED, REMOVED, MODIFIED, SIGNATURE_CHANGED, DEPENDENCY_CHANGED, DOCSTRING_CHANGED, RENAMED.
    Ensures working tree is untouched during git snapshot loading.
    """
    repo_dir = tmp_path / "synthetic_repo"
    repo_dir.mkdir()

    repo = Repo.init(repo_dir)
    repo.git.config("user.name", "Validation Bot")
    repo.git.config("user.email", "val@example.com")

    # =========================================================================
    # COMMIT A (Initial Baseline)
    # =========================================================================
    code_a = """
def process_user_data(user_id: int) -> dict:
    \"\"\"Processes raw user data.\"\"\"
    raw = fetch_raw_data(user_id)
    return {"user_id": user_id, "data": raw}

def fetch_raw_data(user_id: int) -> dict:
    \"\"\"Fetch raw data from DB.\"\"\"
    return {"id": user_id, "status": "active"}

def helper_util(x: int) -> int:
    \"\"\"Helper calculation.\"\"\"
    return x * 42
"""
    (repo_dir / "service.py").write_text(code_a, encoding="utf-8")
    repo.index.add(["service.py"])
    commit_a = repo.index.commit("Commit A: Initial baseline implementation")
    sha_a = commit_a.hexsha

    # =========================================================================
    # COMMIT B (Feature Mutations, Signature, Docstring & Dependency changes)
    # =========================================================================
    code_b = """
def process_user_data(user_id: int, include_metadata: bool = False) -> dict:
    \"\"\"Processes raw user data with validation.\"\"\"
    raw = fetch_raw_data(user_id)
    valid = validate_metadata(raw)
    return {"user_id": user_id, "data": raw, "valid": valid}

def fetch_raw_data(user_id: int) -> dict:
    \"\"\"Fetch raw data from DB.\"\"\"
    return {"id": user_id, "status": "active"}

def helper_util(x: int) -> int:
    \"\"\"Helper calculation.\"\"\"
    return x * 42

def validate_metadata(meta: dict) -> bool:
    \"\"\"Validate metadata format.\"\"\"
    return meta.get("status") == "active"
"""
    (repo_dir / "service.py").write_text(code_b, encoding="utf-8")
    repo.index.add(["service.py"])
    commit_b = repo.index.commit("Commit B: Add metadata validation, change signature & dependencies")
    sha_b = commit_b.hexsha

    # =========================================================================
    # COMMIT C (Renames & Deletions)
    # =========================================================================
    code_c = """
def process_user_data(user_id: int, include_metadata: bool = False) -> dict:
    \"\"\"Processes raw user data with validation.\"\"\"
    valid = validate_metadata({"status": "active"})
    return {"user_id": user_id, "valid": valid}

def compute_multiplier(x: int) -> int:
    \"\"\"Helper calculation.\"\"\"
    return x * 42

def validate_metadata(meta: dict) -> bool:
    \"\"\"Validate metadata format.\"\"\"
    return meta.get("status") == "active"
"""
    (repo_dir / "service.py").write_text(code_c, encoding="utf-8")
    repo.index.add(["service.py"])
    commit_c = repo.index.commit("Commit C: Remove fetch_raw_data and rename helper_util to compute_multiplier")
    sha_c = commit_c.hexsha

    # Save working tree content state to verify loader safety
    working_file = repo_dir / "service.py"
    original_working_content = working_file.read_text(encoding="utf-8")

    # Initialize Engine & Loader
    loader = GitSnapshotLoader(repo_dir)
    engine = SemanticEntityDiffEngine()

    # -------------------------------------------------------------------------
    # VALIDATION 1: COMMIT A vs COMMIT B
    # -------------------------------------------------------------------------
    entities_a, _ = loader.parse_commit_snapshot(sha_a)
    entities_b, _ = loader.parse_commit_snapshot(sha_b)

    diffs_a_b = engine.diff_entities(entities_a, entities_b)
    types_a_b = {d.change_type for d in diffs_a_b}

    assert SemanticChangeType.ADDED in types_a_b, "Failed to detect ADDED (validate_metadata)"
    assert SemanticChangeType.SIGNATURE_CHANGED in types_a_b, "Failed to detect SIGNATURE_CHANGED (process_user_data)"
    assert SemanticChangeType.DEPENDENCY_CHANGED in types_a_b, "Failed to detect DEPENDENCY_CHANGED (process_user_data)"
    assert SemanticChangeType.DOCSTRING_CHANGED in types_a_b, "Failed to detect DOCSTRING_CHANGED (process_user_data)"
    assert SemanticChangeType.MODIFIED in types_a_b, "Failed to detect MODIFIED (process_user_data logic)"

    added_diff = next(d for d in diffs_a_b if d.change_type == SemanticChangeType.ADDED)
    assert added_diff.entity_name == "validate_metadata"

    # -------------------------------------------------------------------------
    # VALIDATION 2: COMMIT B vs COMMIT C
    # -------------------------------------------------------------------------
    entities_c, _ = loader.parse_commit_snapshot(sha_c)

    diffs_b_c = engine.diff_entities(entities_b, entities_c)
    types_b_c = {d.change_type for d in diffs_b_c}

    assert SemanticChangeType.REMOVED in types_b_c, "Failed to detect REMOVED (fetch_raw_data)"
    assert SemanticChangeType.RENAMED in types_b_c, "Failed to detect RENAMED (helper_util -> compute_multiplier)"

    removed_diff = next(d for d in diffs_b_c if d.change_type == SemanticChangeType.REMOVED)
    assert removed_diff.entity_name == "fetch_raw_data"

    renamed_diff = next(d for d in diffs_b_c if d.change_type == SemanticChangeType.RENAMED)
    assert "helper_util" in renamed_diff.entity_name
    assert "compute_multiplier" in renamed_diff.entity_name
    assert renamed_diff.similarity_score >= 0.70

    # -------------------------------------------------------------------------
    # VALIDATION 3: SAFETY & WORKING TREE INTEGRITY
    # -------------------------------------------------------------------------
    current_working_content = working_file.read_text(encoding="utf-8")
    assert current_working_content == original_working_content, "Working tree was mutated by snapshot loader!"

    # Release Git handles for Windows filesystem cleanup
    loader.git_repo.close()
    repo.close()
