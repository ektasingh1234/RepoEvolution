import pytest
from pathlib import Path
from src.reposense.python_parser import PythonASTParser
from src.core.models import EntityType


def test_python_parser_extracts_entities(tmp_path: Path):
    sample_code = """
class DataProcessor:
    \"\"\"Processes repository data.\"\"\"
    def __init__(self, name: str):
        self.name = name

    def compute_stats(self) -> dict:
        \"\"\"Compute basic statistics.\"\"\"
        return {"name": self.name}

def top_level_function(x: int) -> int:
    \"\"\"Calculates double.\"\"\"
    return x * 2
"""
    test_file = tmp_path / "sample.py"
    test_file.write_text(sample_code, encoding="utf-8")

    parser = PythonASTParser()
    assert parser.can_parse(test_file) is True

    entities = parser.parse_file(test_file, repo_root=tmp_path)
    assert len(entities) == 4  # 1 Class, 2 Methods (__init__, compute_stats), 1 Function (top_level_function)

    # Check Class
    cls_entity = next(e for e in entities if e.entity_type == EntityType.CLASS)
    assert cls_entity.name == "DataProcessor"
    assert cls_entity.docstring == "Processes repository data."

    # Check Top-level function
    fn_entity = next(e for e in entities if e.name == "top_level_function")
    assert fn_entity.entity_type == EntityType.FUNCTION
    assert fn_entity.signature == "def top_level_function(x: int) -> int"
    assert fn_entity.docstring == "Calculates double."
