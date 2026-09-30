import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(".").resolve()))

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

repo_dir = str(pathlib.Path(".").resolve())
base_commit = "61a1ad7"
target_commit = "627b3f5"

print(f"=== PHASE 2 SMOKE TEST: SEMANTIC DIFF ({base_commit} vs {target_commit}) ===")

response = client.post(
    "/api/v1/repo/compare",
    json={
        "repo_path": repo_dir,
        "base_commit": base_commit,
        "target_commit": target_commit,
        "top_k": 10,
        "include_explanation": True
    }
)

assert response.status_code == 200, f"Compare failed: {response.text}"
data = response.json()

print(f"Base SHA: {data['base_commit'][:8]} | Target SHA: {data['target_commit'][:8]}")
print(f"Summary Metrics:")
print(f"  Added: {data['summary']['total_added']}")
print(f"  Removed: {data['summary']['total_removed']}")
print(f"  Modified: {data['summary']['total_modified']}")
print(f"  Signature Changed: {data['summary']['total_signature_changed']}")
print(f"  Renamed/Moved: {data['summary']['total_renamed']}")

print("\nCategorized Statements:")
for stmt in data['summary']['categorized_summaries']:
    print(f"  - {stmt}")

print(f"\nEntity Diffs Extracted: {len(data['entity_diffs'])}")
for idx, diff in enumerate(data['entity_diffs'], 1):
    print(f"  #{idx} [{diff['change_type']}] {diff['entity_name']} ({diff['entity_type']}) - Sim: {diff['similarity_score']}")
    print(f"     Evidence: {diff['evidence']}")

print(f"\nModel Used: {data['model_used']}")
print(f"Explanation Snippet:\n{data['llm_explanation'][:300]}...\n")

print("[SUCCESS] PHASE 2 SEMANTIC DIFF SMOKE TEST PASSED PERFECTLY!")
