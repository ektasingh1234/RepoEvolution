import ast
import hashlib
from pathlib import Path
from typing import List, Optional
from src.reposense.base_parser import BaseParser
from src.core.models import CodeEntity, EntityType


class PythonASTVisitor(ast.NodeVisitor):
    """AST Visitor to extract functions, classes, methods, docstrings, and calls."""

    def __init__(self, file_path_rel: str, source_code: str):
        self.file_path_rel = file_path_rel
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.entities: List[CodeEntity] = []
        self.current_class: Optional[str] = None

    def _get_snippet(self, node: ast.AST) -> str:
        if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
            start = node.lineno - 1
            end = node.end_lineno
            return "\n".join(self.lines[start:end])
        return ""

    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _extract_decorators(self, node: ast.FunctionDef | ast.ClassDef) -> List[str]:
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(dec.attr)
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
                elif isinstance(dec.func, ast.Attribute):
                    decorators.append(dec.func.attr)
        return decorators

    def _extract_function_signature(self, node: ast.FunctionDef) -> str:
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation and isinstance(arg.annotation, ast.Name):
                arg_str += f": {arg.annotation.id}"
            args.append(arg_str)
        
        returns = ""
        if node.returns:
            if isinstance(node.returns, ast.Name):
                returns = f" -> {node.returns.id}"
            elif isinstance(node.returns, ast.Constant):
                returns = f" -> {node.returns.value}"

        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({', '.join(args)}){returns}"

    def _extract_calls(self, node: ast.AST) -> List[str]:
        """Extract function/method call names within this AST node."""
        calls = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.add(child.func.attr)
        return sorted(list(calls))

    def visit_ClassDef(self, node: ast.ClassDef):
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)

        docstring = ast.get_docstring(node)
        snippet = self._get_snippet(node)
        sig = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
        
        entity_id = f"{self.file_path_rel}::{node.name}"
        entity = CodeEntity(
            id=entity_id,
            name=node.name,
            entity_type=EntityType.CLASS,
            file_path=self.file_path_rel,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=sig,
            docstring=docstring,
            code_content=snippet,
            content_hash=self._hash_content(snippet),
            dependencies=bases,
            decorators=self._extract_decorators(node),
        )
        self.entities.append(entity)

        # Visit inner functions/methods with class scope
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process_function(node)

    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        docstring = ast.get_docstring(node)
        snippet = self._get_snippet(node)
        sig = self._extract_function_signature(node)
        calls = self._extract_calls(node)

        if self.current_class:
            entity_name = f"{self.current_class}.{node.name}"
            entity_type = EntityType.METHOD
        else:
            entity_name = node.name
            entity_type = EntityType.FUNCTION

        entity_id = f"{self.file_path_rel}::{entity_name}"
        entity = CodeEntity(
            id=entity_id,
            name=entity_name,
            entity_type=entity_type,
            file_path=self.file_path_rel,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=sig,
            docstring=docstring,
            code_content=snippet,
            content_hash=self._hash_content(snippet),
            dependencies=calls,
            decorators=self._extract_decorators(node),
        )
        self.entities.append(entity)


class PythonASTParser(BaseParser):
    """Native Python AST implementation of BaseParser."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".py"]

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions

    def parse_file(self, file_path: Path, repo_root: Path) -> List[CodeEntity]:
        if not self.can_parse(file_path):
            return []

        try:
            rel_path = file_path.relative_to(repo_root).as_posix()
        except ValueError:
            rel_path = file_path.as_posix()

        try:
            source_code = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source_code, filename=str(file_path))
        except Exception:
            return []

        visitor = PythonASTVisitor(rel_path, source_code)
        visitor.visit(tree)
        return visitor.entities
