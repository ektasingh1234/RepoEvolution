import os
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import git

from src.core.models import CodeEntity
from src.reposense.python_parser import PythonASTVisitor


class GitSnapshotLoader:
    """
    Safely inspects file trees and reads file contents at specific Git commits/SHAs
    WITHOUT checking out or altering the user's working tree.
    """

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path).resolve()
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Directory is not a valid Git repository: {repo_path}")
        self.git_repo = git.Repo(self.repo_path)

    def resolve_commit_sha(self, rev: str) -> str:
        """Resolve revision name (HEAD, main, short SHA) to full 40-char SHA."""
        try:
            commit = self.git_repo.commit(rev)
            return commit.hexsha
        except Exception as e:
            raise ValueError(f"Could not resolve Git revision '{rev}': {e}")

    def get_commit_file_tree(self, commit_sha: str) -> Dict[str, str]:
        """
        Extract a map of {relative_file_path: file_content_str} for a specific commit SHA.
        Reads directly from Git tree objects without modifying working directory.
        """
        commit = self.git_repo.commit(commit_sha)
        tree = commit.tree
        files_map: Dict[str, str] = {}

        # Traverse Git tree recursively
        for blob in tree.traverse():
            if blob.type == "blob": # File
                rel_path = blob.path
                if rel_path.endswith(".py"): # Phase 1/2 Python parser target
                    try:
                        content = blob.data_stream.read().decode("utf-8", errors="replace")
                        files_map[rel_path] = content
                    except Exception:
                        continue

        return files_map

    def parse_commit_snapshot(self, commit_sha: str) -> Tuple[List[CodeEntity], Dict[str, str]]:
        """
        Load all supported files at commit_sha and parse their AST entities in memory.
        Returns (entities_list, files_map).
        """
        files_map = self.get_commit_file_tree(commit_sha)
        entities: List[CodeEntity] = []

        for rel_path, source_code in files_map.items():
            try:
                tree = ast.parse(source_code, filename=rel_path)
                visitor = PythonASTVisitor(rel_path, source_code)
                visitor.visit(tree)
                entities.extend(visitor.entities)
            except Exception:
                continue

        return entities, files_map
