from pathlib import Path
from typing import List, Dict, Tuple
import git

from src.core.models import CodeEntity
from src.semantic_diff.git_loader import GitSnapshotLoader


class HistoricalCommitSnapshot:
    """Represents a historical commit AST snapshot."""
    def __init__(self, commit_sha: str, timestamp: int, commit_message: str, entities: List[CodeEntity], files_map: Dict[str, str]):
        self.commit_sha = commit_sha
        self.timestamp = timestamp
        self.commit_message = commit_message
        self.entities = entities
        self.files_map = files_map


class HistoryAnalyzer:
    """
    Safely inspects Git commit history up to history_depth and parses historical AST snapshots.
    Does NOT modify the user's working tree.
    """

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path).resolve()
        self.loader = GitSnapshotLoader(self.repo_path)
        self.git_repo = self.loader.git_repo

    def get_historical_snapshots(
        self, target_commit: str = "HEAD", history_depth: int = 5
    ) -> List[HistoricalCommitSnapshot]:
        """
        Traverse commit history preceding target_commit up to history_depth commits.
        Returns chronological list of HistoricalCommitSnapshot objects.
        """
        target_sha = self.loader.resolve_commit_sha(target_commit)
        
        # Get list of prior commits
        commits = list(self.git_repo.iter_commits(target_sha, max_count=history_depth + 1))
        
        # We need historical preceding commits (excluding target_commit itself if evaluating target vs history)
        historical_commits = commits[1:] if len(commits) > 1 else commits
        
        snapshots: List[HistoricalCommitSnapshot] = []
        for commit in reversed(historical_commits):
            entities, files_map = self.loader.parse_commit_snapshot(commit.hexsha)
            snapshots.append(
                HistoricalCommitSnapshot(
                    commit_sha=commit.hexsha,
                    timestamp=commit.committed_date,
                    commit_message=commit.message.strip(),
                    entities=entities,
                    files_map=files_map
                )
            )

        return snapshots
