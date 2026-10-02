import os
import re
import tempfile
from pathlib import Path
from git import Repo, GitCommandError
from src.core.exceptions import InvalidRepositoryPathError, RepositoryNotFoundError
from src.core.logging_config import get_logger

logger = get_logger(__name__)


def validate_repository_path(path_str: str) -> Path:
    """
    Validates a repository path string or Git URL before filesystem access.

    Performs security checks:
    - Supports local Git repository directory paths.
    - Supports remote Git repository URLs (HTTP/HTTPS/SSH), cloning into a local cache directory.
    - Checks for null bytes, invalid characters, and path traversal attempts.

    Returns:
        Path: Resolved absolute local Path object of target repository.
    Raises:
        InvalidRepositoryPathError: If path contains invalid characters or traversal attempts.
        RepositoryNotFoundError: If directory or Git URL is invalid, inaccessible, or fails clone.
    """
    if not path_str or not isinstance(path_str, str) or not path_str.strip():
        raise InvalidRepositoryPathError("Repository path is invalid or not permitted.")

    # Check for null bytes or control characters
    if "\x00" in path_str:
        raise InvalidRepositoryPathError("Repository path is invalid or not permitted.")

    trimmed_path = path_str.strip()

    # Check if input is a Git URL (e.g. https://github.com/org/repo.git or git@github.com:org/repo.git)
    is_url = (
        trimmed_path.startswith(("http://", "https://", "git@", "git://"))
        or trimmed_path.endswith(".git")
    )

    if is_url:
        try:
            # Extract repository name and compute stable URL hash for cache folder to prevent collisions
            repo_name = trimmed_path.rstrip("/").split("/")[-1].replace(".git", "")
            repo_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', repo_name) or "remote_repo"
            import hashlib
            url_hash = hashlib.sha256(trimmed_path.lower().encode("utf-8")).hexdigest()[:8]
            folder_name = f"{repo_name}_{url_hash}"

            cache_base = Path(tempfile.gettempdir()) / "repo_evolution_cache"
            cache_base.mkdir(parents=True, exist_ok=True)
            target_cache_dir = cache_base / folder_name

            if target_cache_dir.exists() and (target_cache_dir / ".git").exists():
                logger.info(f"Using cached repository clone at {target_cache_dir}")
                return target_cache_dir.resolve()

            if target_cache_dir.exists():
                import shutil
                shutil.rmtree(target_cache_dir, ignore_errors=True)

            logger.info(f"Cloning remote Git repository URL '{trimmed_path}' into '{target_cache_dir}'...")
            Repo.clone_from(trimmed_path, target_cache_dir, depth=10)
            return target_cache_dir.resolve()
        except GitCommandError as gce:
            logger.error(f"Git clone error for URL '{trimmed_path}': {gce}")
            raise RepositoryNotFoundError(f"Failed to clone remote Git URL '{trimmed_path}'. Ensure the repository exists and is publicly accessible.")
        except Exception as ex:
            logger.error(f"Unexpected error processing Git URL '{trimmed_path}': {ex}")
            raise InvalidRepositoryPathError(f"Could not process Git URL '{trimmed_path}': {str(ex)}")

    # Check for path traversal patterns (e.g., ../ or ..\)
    normalized_str = trimmed_path.replace("\\", "/")
    if "/../" in normalized_str or normalized_str.startswith("../") or normalized_str.endswith("/..") or normalized_str == "..":
        raise InvalidRepositoryPathError("Repository path is invalid or not permitted.")

    try:
        raw_path = Path(trimmed_path)
        resolved_path = raw_path.resolve()
    except Exception:
        raise InvalidRepositoryPathError("Repository path is invalid or not permitted.")

    if not resolved_path.exists():
        raise RepositoryNotFoundError("Requested repository directory was not found or is inaccessible.")

    if not resolved_path.is_dir():
        raise InvalidRepositoryPathError("Repository path is invalid or not permitted.")

    return resolved_path
