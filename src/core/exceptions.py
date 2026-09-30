class RepoEvolutionError(Exception):
    """Base exception class for all RepoEvolution domain errors."""

    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class RepositoryNotFoundError(RepoEvolutionError):
    """Raised when a specified repository directory cannot be found."""

    def __init__(self, message: str = "Requested repository directory was not found or is inaccessible."):
        super().__init__(
            message=message,
            error_code="REPOSITORY_NOT_FOUND",
            status_code=404,
        )


class InvalidRepositoryPathError(RepoEvolutionError):
    """Raised when a repository path is invalid or fails security checks (e.g. path traversal)."""

    def __init__(self, message: str = "Repository path is invalid or not permitted."):
        super().__init__(
            message=message,
            error_code="INVALID_REPOSITORY_PATH",
            status_code=400,
        )


class InvalidCommitRefError(RepoEvolutionError):
    """Raised when a specified Git commit SHA or reference is invalid."""

    def __init__(self, message: str = "Invalid or missing Git commit reference."):
        super().__init__(
            message=message,
            error_code="INVALID_COMMIT_REF",
            status_code=404,
        )


class UnsupportedOperationError(RepoEvolutionError):
    """Raised when an operation or file format is unsupported."""

    def __init__(self, message: str = "Requested operation is unsupported."):
        super().__init__(
            message=message,
            error_code="UNSUPPORTED_OPERATION",
            status_code=400,
        )


class InternalProcessingError(RepoEvolutionError):
    """Raised when an internal processing step fails."""

    def __init__(self, message: str = "An internal repository processing failure occurred."):
        super().__init__(
            message=message,
            error_code="INTERNAL_PROCESSING_FAILURE",
            status_code=500,
        )
