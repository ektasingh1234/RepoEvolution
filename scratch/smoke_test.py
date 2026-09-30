import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(".").resolve()))
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

repo_path = str(pathlib.Path(".").resolve())
print(f"=== 1. SMOKE TEST: INGESTING REPOSITORY ({repo_path}) ===")
r1 = client.post("/api/v1/repo/ingest", json={"repo_path": repo_path})
assert r1.status_code == 200, f"Ingest failed: {r1.text}"
ingest_data = r1.json()
print(f"Status: {ingest_data['status']}")
print(f"Parsed Files: {ingest_data['total_files_parsed']} | Entities Extracted: {ingest_data['total_entities_extracted']}")
print(f"Entity Breakdown: {ingest_data['entity_counts']}\n")

print("=== 2. SMOKE TEST: REPOSITORY OVERVIEW ===")
r2 = client.get("/api/v1/repo/overview")
assert r2.status_code == 200
overview_data = r2.json()
print(f"Status: {overview_data['status']}")
print(f"Total Entities: {overview_data['total_entities']}\n")

print("=== 3. SMOKE TEST: HYBRID DENSE + SPARSE SEARCH ===")
r3 = client.post("/api/v1/repo/search", json={"query": "AST parser entity extraction", "top_k": 3})
assert r3.status_code == 200
search_data = r3.json()
print(f"Query: '{search_data['query']}' | Results Count: {search_data['total_results']}")
for idx, res in enumerate(search_data["results"], 1):
    entity = res["entity"]
    print(f"  Result #{idx}: {entity['name']} ({entity['entity_type']}) - Score: {res['score']} [{res['retrieval_type']}]")
    print(f"    File: {entity['file_path']} (L{entity['start_line']}-L{entity['end_line']})")
print()

print("=== 4. SMOKE TEST: CHANGEGRAPH DEPENDENCY MATRIX ===")
r4 = client.get("/api/v1/graph/data")
assert r4.status_code == 200
graph_data = r4.json()
print(f"Graph Nodes Count: {len(graph_data['nodes'])} | Edge Dependencies Count: {len(graph_data['edges'])}\n")

print("=== 5. SMOKE TEST: GROUNDED COPILOT (OFFLINE / RETRIEVAL MODE) ===")
r5 = client.post("/api/v1/copilot/ask", json={"question": "How does PythonASTParser extract code entities?", "top_k": 3})
assert r5.status_code == 200
copilot_data = r5.json()
print(f"Model Used: {copilot_data['model_used']}")
print(f"Citations Count: {len(copilot_data['citations'])}")
print("Sample Citations:")
for cite in copilot_data["citations"]:
    print(f"  - {cite['reference']} ({cite['snippet']})")

print("\n[SUCCESS] ALL 5 SMOKE TESTS PASSED PERFECTLY!")
