from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from src.core.models import CodeEntity


class BaseParser(ABC):
    """
    Abstract Base Class for language-specific code parsers.
    Ensures extensibility for Python (AST), JavaScript/TypeScript (Tree-sitter), Java, C++, etc.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """List of file extensions supported by this parser (e.g. ['.py'])."""
        pass

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if the given file can be parsed by this parser instance."""
        pass

    @abstractmethod
    def parse_file(self, file_path: Path, repo_root: Path) -> List[CodeEntity]:
        """
        Parse a single file and return a list of extracted CodeEntity objects.
        
        :param file_path: Absolute path to target file.
        :param repo_root: Absolute path to root of repository (for computing relative file paths).
        :return: List of CodeEntity schemas.
        """
        pass
