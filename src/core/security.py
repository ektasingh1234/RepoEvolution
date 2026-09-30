from pathlib import Path
from src.core.exceptions import InvalidRepositoryPathError, RepositoryNotFoundError


def validate_repository_path(path_str: str) -> Path:
    """
    Validates a repository path string before filesystem access.

    Performs security checks:
    - Checks for empty path or null-byte insertion
    - Checks for explicit path traversal attempts
    - Resolves path safely
    - Verifies path exists and is a directory

    Returns:
        Path: Resolved absolute Path object.
    Raises:
        InvalidRepositoryPathError: If path contains invalid characters or traversal attempts.
        RepositoryNotFoundError: If directory does not exist or is not a directory.
    """
    if not path_str or not isinstance(path_str, str) or not path_str.strip():
        raise InvalidRepositoryPathError("Repository path is invalid or not permitted.")

    # Check for null bytes or control characters
    if "\x00" in path_str:
        raise InvalidRepositoryPathError("Repository path is invalid or not permitted.")

    # Check for path traversal patterns (e.g., ../ or ..\)
    normalized_str = path_str.replace("\\", "/")
    if "/../" in normalized_str or normalized_str.startswith("../") or normalized_str.endswith("/..") or normalized_str == "..":
        raise InvalidRepositoryPathError("Repository path is invalid or not permitted.")

    try:
        raw_path = Path(path_str)
        resolved_path = raw_path.resolve()
    except Exception:
        raise InvalidRepositoryPathError("Repository path is invalid or not permitted.")

    if not resolved_path.exists():
        raise RepositoryNotFoundError("Requested repository directory was not found or is inaccessible.")

    if not resolved_path.is_dir():
        raise InvalidRepositoryPathError("Repository path is invalid or not permitted.")

    return resolved_path
