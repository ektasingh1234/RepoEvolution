import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import settings
from src.reposense.indexer import RepositoryIndexer
from src.copilot.llm_provider import GeminiProvider

def run_real_gemini_test():
    # 1. Verify environment configuration detected (without printing key)
    api_key_set = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    print(f"API configuration detected: {'YES' if api_key_set else 'NO'}")

    # 2. Initialize GeminiProvider
    provider = GeminiProvider()
    model_name = provider.get_available_model_name()
    print(f"Initialized GeminiProvider active model: {model_name}")

    # 3. Perform RepoSense retrieval over actual RepoEvolution codebase
    repo_dir = settings.BASE_DIR
    print(f"Indexing repository at: {repo_dir}")
    indexer = RepositoryIndexer()
    indexer.index_repository(repo_dir)

    question = "How does RepoEvolution perform Python AST entity extraction, and which component is responsible for extracting function and class entities?"
    search_results = indexer.search(question, top_k=5)

    retrieved_entities = [r.entity for r in search_results]
    print(f"Retrieved {len(retrieved_entities)} repository code entities.")

    # Format grounded evidence bundle
    evidence_lines = []
    for r in search_results:
        e = r.entity
        evidence_lines.append(
            f"File: {e.file_path} (Lines {e.start_line}-{e.end_line})\n"
            f"Entity: {e.name} ({e.entity_type.value})\n"
            f"Signature: {e.signature}\n"
            f"Docstring: {e.docstring or 'None'}\n"
            f"Content Snippet:\n{e.code_content[:500]}\n"
            f"---"
        )
    evidence_bundle = "\n\n".join(evidence_lines)

    # 4. Perform Real Gemini API request
    t0 = time.perf_counter()
    copilot_response = provider.generate_grounded_answer(
        question=question,
        retrieved_entities=retrieved_entities,
        evidence_summary=evidence_bundle
    )
    t_elapsed = (time.perf_counter() - t0) * 1000

    print(f"Real Gemini Request Status: {'SUCCESS' if copilot_response.groundedness_score > 0 and 'Error' not in copilot_response.answer else 'FAILURE'}")
    print(f"Model actually used: {copilot_response.model_used}")
    print(f"Response latency: {t_elapsed:.2f} ms")
    print(f"Citations count: {len(copilot_response.citations)}")
    print("\n--- Answer Output Preview ---")
    print(copilot_response.answer)
    print("-----------------------------\n")

if __name__ == "__main__":
    run_real_gemini_test()
