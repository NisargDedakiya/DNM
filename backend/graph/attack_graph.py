import logging
from typing import Dict, List, Any
import networkx as nx

logger = logging.getLogger(__name__)

class AttackGraph:
    """Manages the graph representation of attack paths and relationships."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        
    def add_node(self, node_id: str, node_type: str, metadata: Dict[str, Any] = None):
        """
        Types: 'asset', 'endpoint', 'finding', 'auth_system', 'api', 'cloud_asset'
        """
        self.graph.add_node(node_id, type=node_type, **(metadata or {}))
        
    def add_edge(self, source_id: str, target_id: str, edge_type: str, weight: float = 1.0):
        """
        Types: 'hosts', 'exposes', 'exploits_to', 'authenticates'
        """
        self.graph.add_edge(source_id, target_id, type=edge_type, weight=weight)
        
    def get_neighbors(self, node_id: str) -> List[str]:
        if node_id in self.graph:
            return list(self.graph.successors(node_id))
        return []
        
    def find_paths(self, source_id: str, target_id: str, max_depth: int = 5) -> List[List[str]]:
        """Find attack paths between nodes."""
        if source_id in self.graph and target_id in self.graph:
            return list(nx.all_simple_paths(self.graph, source_id, target_id, cutoff=max_depth))
        return []
