import networkx as nx
from typing import Dict, Any, List

class TopologyGraph:
    """
    Maintains an in-memory graph representation of the Kubernetes cluster topology.
    Nodes represent Pods, Services, and Nodes. Edges represent dependencies and physical placements.
    """
    def __init__(self):
        self.graph = nx.DiGraph()

    def update_node(self, node_id: str, node_type: str, attributes: Dict[str, Any]):
        """Add or update a node in the graph."""
        self.graph.add_node(node_id, type=node_type, **attributes)

    def add_dependency(self, source_id: str, target_id: str, relation_type: str = "calls"):
        """Add a dependency edge between two nodes."""
        self.graph.add_edge(source_id, target_target_id=target_id, relation=relation_type)

    def remove_node(self, node_id: str):
        """Remove a node if it no longer exists in the cluster."""
        if self.graph.has_node(node_id):
            self.graph.remove_node(node_id)

    def get_node_state(self, node_id: str) -> Dict[str, Any]:
        """Retrieve the current state/metrics of a node."""
        return self.graph.nodes.get(node_id, {})

    def get_dependencies(self, node_id: str) -> List[str]:
        """Get a list of nodes that this node depends on."""
        if self.graph.has_node(node_id):
            return list(self.graph.successors(node_id))
        return []

    def get_dependents(self, node_id: str) -> List[str]:
        """Get a list of nodes that depend on this node."""
        if self.graph.has_node(node_id):
            return list(self.graph.predecessors(node_id))
        return []

    def to_dict(self) -> Dict[str, Any]:
        """Export the graph as a dictionary (e.g., for JSON serialization)."""
        return nx.node_link_data(self.graph)
