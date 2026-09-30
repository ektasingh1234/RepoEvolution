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
