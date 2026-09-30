from pathlib import Path
from fastapi import APIRouter, HTTPException
from src.core.config import settings
from src.core.models import DriftRequest, DriftResponse
from src.driftguard.history_analyzer import HistoryAnalyzer
from src.driftguard.pattern_extractor import PatternExtractor
from src.driftguard.drift_engine import DriftDetectionEngine
from src.semantic_diff.git_loader import GitSnapshotLoader
from src.copilot.llm_provider import GeminiProvider
from src.api.routes.repo import current_repo_path

router = APIRouter(prefix="/api/v1", tags=["DriftGuard Operations"])

global_llm_provider = GeminiProvider()


from src.core.security import validate_repository_path
from src.core.exceptions import InvalidRepositoryPathError, InvalidCommitRefError, RepoEvolutionError, InternalProcessingError

@router.post("/repo/drift", response_model=DriftResponse)
def detect_repository_drift(payload: DriftRequest):
    repo_dir_str = payload.repo_path or current_repo_path or str(settings.BASE_DIR)
    repo_dir = validate_repository_path(repo_dir_str)

    if not (repo_dir / ".git").exists():
        raise InvalidRepositoryPathError(f"Target path is not a valid Git repository: {repo_dir_str}")

    try:
        # 1. Analyze historical commits
        history_analyzer = HistoryAnalyzer(repo_dir)
        snapshots = history_analyzer.get_historical_snapshots(
            target_commit=payload.target_commit,
            history_depth=payload.history_depth
        )

        # 2. Extract historical patterns
        patterns = PatternExtractor.extract_patterns(snapshots)

        # 3. Load target commit AST snapshot
        loader = GitSnapshotLoader(repo_dir)
        target_sha = loader.resolve_commit_sha(payload.target_commit)
        target_entities, _ = loader.parse_commit_snapshot(target_sha)

        # 4. Detect drift using deterministic engine
        engine = DriftDetectionEngine(min_confidence=payload.min_confidence)
        findings = engine.detect_drift(target_entities, patterns)

        explanation = None
        model_name = "offline-drift-retriever"

        # 5. Generate optional LLM Explanation
        if payload.include_explanation:
            findings_lines = []
            for f in findings:
                findings_lines.append(
                    f"[{f.drift_type.value}] ({f.severity.value}) Entity: '{f.entity}'\n"
                    f"  Historical Pattern: {f.historical_pattern}\n"
                    f"  Current Pattern: {f.current_pattern}\n"
                    f"  Evidence Commits: {[c[:8] for c in f.evidence_commits]}\n"
                    f"  Confidence: {f.confidence:.2f}\n"
                    f"  Recommendation Basis: {f.recommendation_basis}\n"
                )
            findings_details_text = "\n".join(findings_lines) if findings_lines else "No architectural drift findings detected."

            try:
                system_template = settings.get_prompt_template("driftguard_system.txt")
            except FileNotFoundError:
                system_template = "Analyze Drift:\n<driftguard_evidence>\nTarget: {target_commit}\nFindings:\n{findings_details}\n</driftguard_evidence>"

            full_prompt = system_template.format(
                target_commit=target_sha[:8],
                min_confidence=payload.min_confidence,
                total_findings=len(findings),
                findings_details=findings_details_text
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
                    explanation = f"LLM generation warning: {e}"
            else:
                explanation = (
                    f"### [Offline DriftGuard Evidence Explanation]\n\n"
                    f"**Target Commit:** `{target_sha[:8]}` | **Min Confidence Threshold:** `{payload.min_confidence}`\n\n"
                    f"#### Summary of Findings ({len(findings)} detected):\n"
                    + ("\n".join([f"- **[{f.drift_type.value}]** `{f.entity}`: {f.description} (Confidence: {f.confidence:.2f})" for f in findings]) if findings else "- No drift findings detected above confidence threshold.")
                    + "\n\n*(Note: GEMINI_API_KEY is unconfigured/offline. Structured DriftGuard evidence computed directly.)*"
                )

        return DriftResponse(
            repo_path=str(repo_dir),
            target_commit=target_sha,
            findings=findings,
            total_findings=len(findings),
            llm_explanation=explanation,
            model_used=model_name
        )

    except ValueError:
        raise InvalidCommitRefError("Invalid or missing Git commit reference.")
    except RepoEvolutionError:
        raise
    except Exception:
        raise InternalProcessingError("An internal architectural drift detection failure occurred.")
