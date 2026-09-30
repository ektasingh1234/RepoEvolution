import pytest
import os
import tempfile
from pathlib import Path
from git import Repo
from fastapi.testclient import TestClient

from src.core.models import (
    CodeEntity, EntityType, SemanticChangeType, CompareRequest
)
from src.semantic_diff.entity_diff import SemanticEntityDiffEngine
from src.semantic_diff.summary_builder import SemanticSummaryBuilder
from src.semantic_diff.git_loader import GitSnapshotLoader
from src.api.main import app

client = TestClient(app)


def test_added_entity_diff():
    base_entities = []
    target_entities = [
        CodeEntity(
            id="auth.py::new_login",
            name="new_login",
            entity_type=EntityType.FUNCTION,
            file_path="auth.py",
            start_line=1,
            end_line=5,
            signature="def new_login(user: str)",
            code_content="def new_login(user: str):\n    return True",
            content_hash="hash1",
            dependencies=[]
        )
    ]

    engine = SemanticEntityDiffEngine()
    diffs = engine.diff_entities(base_entities, target_entities)

    assert len(diffs) == 1
    assert diffs[0].change_type == SemanticChangeType.ADDED
    assert diffs[0].entity_name == "new_login"


def test_removed_entity_diff():
    base_entities = [
        CodeEntity(
            id="old.py::deprecated_func",
            name="deprecated_func",
            entity_type=EntityType.FUNCTION,
            file_path="old.py",
            start_line=1,
            end_line=5,
            signature="def deprecated_func()",
            code_content="def deprecated_func(): pass",
            content_hash="hash0",
            dependencies=[]
        )
    ]
    target_entities = []

    engine = SemanticEntityDiffEngine()
    diffs = engine.diff_entities(base_entities, target_entities)

    assert len(diffs) == 1
    assert diffs[0].change_type == SemanticChangeType.REMOVED
    assert diffs[0].entity_name == "deprecated_func"


def test_signature_and_logic_modified_diff():
    base_entity = CodeEntity(
        id="calc.py::add",
        name="add",
        entity_type=EntityType.FUNCTION,
        file_path="calc.py",
        start_line=1,
        end_line=3,
        signature="def add(a, b)",
        code_content="def add(a, b):\n    return a + b",
        content_hash="h1",
        dependencies=[]
    )

    target_entity = CodeEntity(
        id="calc.py::add",
        name="add",
        entity_type=EntityType.FUNCTION,
        file_path="calc.py",
        start_line=1,
        end_line=3,
        signature="def add(a: int, b: int) -> int",
        code_content="def add(a: int, b: int) -> int:\n    return int(a + b)",
        content_hash="h2",
        dependencies=[]
    )

    engine = SemanticEntityDiffEngine()
    diffs = engine.diff_entities([base_entity], [target_entity])

    # Expect signature change and logic modification
    change_types = [d.change_type for d in diffs]
    assert SemanticChangeType.SIGNATURE_CHANGED in change_types
    assert SemanticChangeType.MODIFIED in change_types


def test_dependency_changed_diff():
    base_entity = CodeEntity(
        id="service.py::run",
        name="run",
        entity_type=EntityType.FUNCTION,
        file_path="service.py",
        start_line=1,
        end_line=5,
        signature="def run()",
        code_content="def run(): step1()",
        content_hash="h1",
        dependencies=["step1"]
    )

    target_entity = CodeEntity(
        id="service.py::run",
        name="run",
        entity_type=EntityType.FUNCTION,
        file_path="service.py",
        start_line=1,
        end_line=5,
        signature="def run()",
        code_content="def run(): step1(); step2()",
        content_hash="h2",
        dependencies=["step1", "step2"]
    )

    engine = SemanticEntityDiffEngine()
    diffs = engine.diff_entities([base_entity], [target_entity])

    change_types = [d.change_type for d in diffs]
    assert SemanticChangeType.DEPENDENCY_CHANGED in change_types


def test_renamed_entity_diff():
    base_entity = CodeEntity(
        id="utils.py::old_name",
        name="old_name",
        entity_type=EntityType.FUNCTION,
        file_path="utils.py",
        start_line=1,
        end_line=5,
        signature="def old_name(val)",
        code_content="def old_name(val):\n    print('complex logic')\n    return val * 100",
        content_hash="h1",
        dependencies=[]
    )

    target_entity = CodeEntity(
        id="utils.py::new_name",
        name="new_name",
        entity_type=EntityType.FUNCTION,
        file_path="utils.py",
        start_line=10,
        end_line=15,
        signature="def new_name(val)",
        code_content="def new_name(val):\n    print('complex logic')\n    return val * 100",
        content_hash="h1",
        dependencies=[]
    )

    engine = SemanticEntityDiffEngine()
    diffs = engine.diff_entities([base_entity], [target_entity])

    assert len(diffs) == 1
    assert diffs[0].change_type == SemanticChangeType.RENAMED
    assert diffs[0].similarity_score >= 0.70


def test_git_snapshot_loader_integration(tmp_path: Path):
    """
    Integration test creating a real temporary Git repo with 2 commits,
    verifying GitSnapshotLoader and SemanticDiff end-to-end without touching working directory.
    """
    repo_dir = tmp_path / "test_git_repo"
    repo_dir.mkdir()

    repo = Repo.init(repo_dir)
    repo.git.config("user.name", "Test User")
    repo.git.config("user.email", "test@example.com")

    # Commit 1 (Base): Create initial auth.py
    file_a = repo_dir / "auth.py"
    file_a.write_text("def authenticate(user):\n    return True\n", encoding="utf-8")
    repo.index.add(["auth.py"])
    commit1 = repo.index.commit("Initial commit: add auth.py")
    sha1 = commit1.hexsha

    # Commit 2 (Target): Modify auth.py & add payment.py
    file_a.write_text("def authenticate(user: str, token: str) -> bool:\n    return token == 'valid'\n", encoding="utf-8")
    file_b = repo_dir / "payment.py"
    file_b.write_text("def process_charge(amount: float):\n    pass\n", encoding="utf-8")
    repo.index.add(["auth.py", "payment.py"])
    commit2 = repo.index.commit("Second commit: modify auth & add payment")
    sha2 = commit2.hexsha

    # Verify Snapshot Loader reads commits cleanly
    loader = GitSnapshotLoader(repo_dir)
    c1_entities, c1_files = loader.parse_commit_snapshot(sha1)
    c2_entities, c2_files = loader.parse_commit_snapshot(sha2)

    assert len(c1_entities) == 1
    assert c1_entities[0].name == "authenticate"

    assert len(c2_entities) == 2

    # Verify Semantic Diff between Commit 1 and Commit 2
    engine = SemanticEntityDiffEngine()
    diffs = engine.diff_entities(c1_entities, c2_entities)
    summary = SemanticSummaryBuilder.build_summary(diffs)

    assert summary.total_added >= 1  # payment.py process_charge added
    assert summary.total_signature_changed >= 1  # authenticate signature changed

    # Test FastAPI compare endpoint
    response = client.post(
        "/api/v1/repo/compare",
        json={
            "repo_path": str(repo_dir),
            "base_commit": sha1,
            "target_commit": sha2,
            "include_explanation": True
        }
    )
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["base_commit"] == sha1
    assert res_json["target_commit"] == sha2
    assert res_json["summary"]["total_added"] >= 1
    assert len(res_json["entity_diffs"]) >= 1
