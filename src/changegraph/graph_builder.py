import networkx as nx
from typing import List, Dict, Optional
from src.core.models import CodeEntity, GraphData, GraphNode, GraphEdge


class DependencyGraphBuilder:
    """
    Constructs and manages NetworkX directed call/import dependency graph.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def build_graph(self, entities: List[CodeEntity]) -> nx.DiGraph:
        """
        Build NetworkX DiGraph from a list of CodeEntity objects.
        """
        self.graph.clear()
        name_to_id_map: Dict[str, str] = {}

        # 1. Add all entities as nodes & populate name lookup map
        for entity in entities:
            self.graph.add_node(
                entity.id,
                label=entity.name,
                entity_type=entity.entity_type.value,
                file_path=entity.file_path,
                start_line=entity.start_line,
                end_line=entity.end_line,
                signature=entity.signature
            )
            # Map simple name & qualified name to ID
            name_to_id_map[entity.name] = entity.id
            if "." in entity.name:
                short_name = entity.name.split(".")[-1]
                if short_name not in name_to_id_map:
                    name_to_id_map[short_name] = entity.id

        # 2. Add edges based on extracted dependencies (calls / base classes)
        for entity in entities:
            for dep in entity.dependencies:
                # Check if dep matches another known entity ID or name
                target_id = None
                if dep in self.graph:
                    target_id = dep
                elif dep in name_to_id_map:
                    target_id = name_to_id_map[dep]

                if target_id and target_id != entity.id:
                    self.graph.add_edge(entity.id, target_id, relation="calls")

        return self.graph

    def get_graph_data(self) -> GraphData:
        """Export NetworkX graph to serializable Pydantic GraphData for frontend UI."""
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []

        for node_id, data in self.graph.nodes(data=True):
            nodes.append(
                GraphNode(
                    id=node_id,
                    label=data.get("label", node_id),
                    type=data.get("entity_type", "unknown"),
                    file_path=data.get("file_path", "")
                )
            )

        for u, v, data in self.graph.edges(data=True):
            edges.append(
                GraphEdge(
                    source=u,
                    target=v,
                    relation=data.get("relation", "calls")
                )
            )

        return GraphData(nodes=nodes, edges=edges)

    def compute_impact(self, target_entity_id: str) -> List[str]:
        """
        Compute direct and indirect downstream nodes affected if target_entity_id changes.
        """
        if target_entity_id not in self.graph:
            return []

        # Find ancestors (entities that depend on/call target_entity_id)
        affected = nx.ancestors(self.graph, target_entity_id)
        return list(affected)
