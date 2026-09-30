from pathlib import Path
from fastapi import APIRouter, HTTPException
from src.core.config import settings
from src.core.models import CompareRequest, CompareResponse
from src.semantic_diff.git_loader import GitSnapshotLoader
from src.semantic_diff.entity_diff import SemanticEntityDiffEngine
from src.semantic_diff.summary_builder import SemanticSummaryBuilder
from src.copilot.llm_provider import GeminiProvider
from src.api.routes.repo import current_repo_path

router = APIRouter(prefix="/api/v1", tags=["Semantic Diff Operations"])

global_diff_engine = SemanticEntityDiffEngine()
global_llm_provider = GeminiProvider()


from src.core.security import validate_repository_path
from src.core.exceptions import InvalidRepositoryPathError, InvalidCommitRefError, RepoEvolutionError, InternalProcessingError

@router.post("/repo/compare", response_model=CompareResponse)
def compare_repository_commits(payload: CompareRequest):
    repo_dir_str = payload.repo_path or current_repo_path or str(settings.BASE_DIR)
    repo_dir = validate_repository_path(repo_dir_str)

    if not (repo_dir / ".git").exists():
        raise InvalidRepositoryPathError(f"Target path is not a valid Git repository: {repo_dir_str}")

    try:
        loader = GitSnapshotLoader(repo_dir)
        base_sha = loader.resolve_commit_sha(payload.base_commit)
        target_sha = loader.resolve_commit_sha(payload.target_commit)

        base_entities, _ = loader.parse_commit_snapshot(base_sha)
        target_entities, _ = loader.parse_commit_snapshot(target_sha)

        diffs = global_diff_engine.diff_entities(base_entities, target_entities)
        summary = SemanticSummaryBuilder.build_summary(diffs)

        # Slice top_k diffs
        top_diffs = diffs[:payload.top_k]

        explanation = None
        model_name = "offline-summary-retriever"

        if payload.include_explanation:
            diff_lines = []
            for d in top_diffs:
                diff_lines.append(
                    f"[{d.change_type.value}] {d.entity_name} ({d.entity_type.value})\n"
                    f"  Files: before='{d.file_before}', after='{d.file_after}'\n"
                    f"  Evidence: {d.evidence}\n"
                    f"  Dependencies affected: {d.affected_dependencies}\n"
                )
            diff_details_text = "\n".join(diff_lines) if diff_lines else "No entity diffs detected."
            summary_text = " | ".join(summary.categorized_summaries)

            try:
                system_template = settings.get_prompt_template("prompt_semantic_diff.txt")
            except FileNotFoundError:
                system_template = "Analyze AST changes:\n<semantic_diff_evidence>\nBase: {base_commit}\nTarget: {target_commit}\nSummary: {summary_text}\nDiffs:\n{diff_details}\n</semantic_diff_evidence>"

            full_prompt = system_template.format(
                base_commit=base_sha[:8],
                target_commit=target_sha[:8],
                summary_text=summary_text,
                total_diffs=len(diffs),
                diff_details=diff_details_text
            )

            if global_llm_provider.client and global_llm_provider.api_key:
                try:
                    res = global_llm_provider.client.models.generate_content(
                        model=global_llm_provider.active_model,
                        contents=full_prompt
                    )
                    explanation = res.text or "No explanation generated."
                    model_name = global_llm_provider.active_model
                except Exception as e:
                    explanation = f"LLM generation warning: {e}\n\nEvidence Summary:\n{summary_text}"
            else:
                explanation = (
                    f"### [Offline SemanticDiff Evidence Explanation]\n\n"
                    f"**Base Commit:** `{base_sha[:8]}` | **Target Commit:** `{target_sha[:8]}`\n\n"
                    f"#### High-Level Categorized Summary:\n"
                    + "\n".join([f"- {s}" for s in summary.categorized_summaries])
                    + "\n\n*(Note: GEMINI_API_KEY is unconfigured/offline. Structured AST diff evidence computed directly.)*"
                )

        return CompareResponse(
            base_commit=base_sha,
            target_commit=target_sha,
            summary=summary,
            entity_diffs=top_diffs,
            llm_explanation=explanation,
            model_used=model_name
        )

    except ValueError:
        raise InvalidCommitRefError("Invalid or missing Git commit reference.")
    except RepoEvolutionError:
        raise
    except Exception:
        raise InternalProcessingError("An internal repository comparison failure occurred.")
