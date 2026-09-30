import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from src.api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "REPOEVOLUTION"
    assert data["status"] == "online"


def test_ingest_and_overview(tmp_path: Path):
    sample_code = """
def sample_func():
    return 42
"""
    (tmp_path / "main.py").write_text(sample_code, encoding="utf-8")

    # 1. Ingest repo
    ingest_resp = client.post(
        "/api/v1/repo/ingest",
        json={"repo_path": str(tmp_path)}
    )
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    assert ingest_data["total_files_parsed"] == 1
    assert ingest_data["total_entities_extracted"] == 1

    # 2. Get overview
    overview_resp = client.get("/api/v1/repo/overview")
    assert overview_resp.status_code == 200
    overview_data = overview_resp.json()
    assert overview_data["status"] == "ready"
    assert overview_data["total_entities"] == 1

    # 3. Search code
    search_resp = client.post(
        "/api/v1/repo/search",
        json={"query": "sample_func", "top_k": 1}
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total_results"] == 1
    assert search_data["results"][0]["entity"]["name"] == "sample_func"

    # 4. Ask Copilot
    copilot_resp = client.post(
        "/api/v1/copilot/ask",
        json={"question": "What does sample_func do?", "top_k": 1}
    )
    assert copilot_resp.status_code == 200
    copilot_data = copilot_resp.json()
    assert "answer" in copilot_data
    assert len(copilot_data["citations"]) >= 1


def test_ingest_nonexistent_repository_path():
    fake_path = "/nonexistent/fake/repository/path/12345"
    response = client.post(
        "/api/v1/repo/ingest",
        json={"repo_path": fake_path}
    )
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "REPOSITORY_NOT_FOUND"
    # Ensure raw user path is NOT exposed in the error message for security
    assert fake_path not in data["message"]


def test_ingest_path_traversal_attempt():
    traversal_path = "../../../etc/passwd"
    response = client.post(
        "/api/v1/repo/ingest",
        json={"repo_path": traversal_path}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_REPOSITORY_PATH"
    # Ensure raw traversal path is NOT leaked in response
    assert traversal_path not in data["message"]


def test_ingest_empty_path():
    response = client.post(
        "/api/v1/repo/ingest",
        json={"repo_path": ""}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_REPOSITORY_PATH"


def test_ingest_null_byte_path():
    response = client.post(
        "/api/v1/repo/ingest",
        json={"repo_path": "/some/path\x00with_null"}
    )
    assert response.status_code in (400, 422)


def test_malformed_request_payload():
    response = client.post(
        "/api/v1/repo/ingest",
        json={"invalid_key": 123}
    )
    assert response.status_code == 422


def test_compare_non_git_repository(tmp_path: Path):
    response = client.post(
        "/api/v1/repo/compare",
        json={"repo_path": str(tmp_path), "base_commit": "HEAD~1", "target_commit": "HEAD"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_REPOSITORY_PATH"


def test_drift_non_git_repository(tmp_path: Path):
    response = client.post(
        "/api/v1/repo/drift",
        json={"repo_path": str(tmp_path), "target_commit": "HEAD"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_REPOSITORY_PATH"


def test_security_validator_unit():
    from src.core.security import validate_repository_path
    from src.core.exceptions import InvalidRepositoryPathError, RepositoryNotFoundError

    # Valid directory
    valid_p = validate_repository_path(str(Path.cwd()))
    assert valid_p.is_dir()

    # Traversal error
    with pytest.raises(InvalidRepositoryPathError) as exc_info:
        validate_repository_path("../../../some_path")
    assert "../../../some_path" not in str(exc_info.value)

    # Nonexistent error
    with pytest.raises(RepositoryNotFoundError) as exc_info:
        validate_repository_path("C:/nonexistent_repo_dir_999")
    assert "nonexistent_repo_dir_999" not in str(exc_info.value)
