import pytest
from src.core.models import CodeEntity, EntityType
from src.changegraph.graph_builder import DependencyGraphBuilder


def test_dependency_graph_builder():
    entities = [
        CodeEntity(
            id="auth.py::login",
            name="login",
            entity_type=EntityType.FUNCTION,
            file_path="auth.py",
            start_line=1,
            end_line=10,
            signature="def login()",
            code_content="def login(): validate_token()",
            content_hash="abc123",
            dependencies=["validate_token"]
        ),
        CodeEntity(
            id="auth.py::validate_token",
            name="validate_token",
            entity_type=EntityType.FUNCTION,
            file_path="auth.py",
            start_line=12,
            end_line=20,
            signature="def validate_token()",
            code_content="def validate_token(): pass",
            content_hash="def456",
            dependencies=[]
        )
    ]

    builder = DependencyGraphBuilder()
    graph = builder.build_graph(entities)

    assert "auth.py::login" in graph.nodes
    assert "auth.py::validate_token" in graph.nodes

    # Check edge: login calls validate_token
    assert graph.has_edge("auth.py::login", "auth.py::validate_token")

    # Check impact computation: if validate_token changes, login is affected
    affected = builder.compute_impact("auth.py::validate_token")
    assert "auth.py::login" in affected
