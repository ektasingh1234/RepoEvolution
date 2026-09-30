import pytest
from pathlib import Path
from src.reposense.indexer import RepositoryIndexer


def test_indexer_scanning_and_hybrid_search(tmp_path: Path):
    code_a = """
def authenticate_user(username: str, password_hash: str) -> bool:
    \"\"\"Authenticate a user with username and password hash.\"\"\"
    return username == "admin"
"""
    code_b = """
def process_payment(amount: float, currency: str) -> str:
    \"\"\"Process credit card payment transaction.\"\"\"
    return "tx_12345"
"""
    (tmp_path / "auth.py").write_text(code_a, encoding="utf-8")
    (tmp_path / "payment.py").write_text(code_b, encoding="utf-8")

    indexer = RepositoryIndexer()
    files_count, entities_count = indexer.index_repository(tmp_path)

    assert files_count == 2
    assert entities_count == 2

    # Test Hybrid Search for authentication query
    results = indexer.search(query="how to log in user authentication", top_k=2)
    assert len(results) > 0
    top_entity = results[0].entity
    assert top_entity.name == "authenticate_user"
    assert top_entity.file_path in ("auth.py", str(tmp_path / "auth.py"))
