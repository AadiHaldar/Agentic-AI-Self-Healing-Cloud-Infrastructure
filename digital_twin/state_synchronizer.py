import time
import requests
import logging
from typing import Optional
from .topology_graph import TopologyGraph

logger = logging.getLogger(__name__)

class StateSynchronizer:
    """
    Connects to Prometheus (and eventually Kafka) to fetch the latest metrics and state 
    of the cluster, pushing them into the TopologyGraph.
    """
    def __init__(self, prometheus_url: str, topology_graph: TopologyGraph):
        self.prometheus_url = prometheus_url
        self.topology_graph = topology_graph

    def fetch_cpu_usage(self) -> dict:
        """Fetch CPU usage for all pods in the online-boutique namespace."""
        query = 'rate(container_cpu_usage_seconds_total{namespace="online-boutique"}[1m])'
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/query", params={'query': query})
            response.raise_for_status()
            return response.json()['data']['result']
        except Exception as e:
            logger.error(f"Failed to fetch CPU metrics: {e}")
            return []

    def fetch_memory_usage(self) -> dict:
        """Fetch memory usage for all pods in the online-boutique namespace."""
        query = 'container_memory_usage_bytes{namespace="online-boutique"}'
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/query", params={'query': query})
            response.raise_for_status()
            return response.json()['data']['result']
        except Exception as e:
            logger.error(f"Failed to fetch Memory metrics: {e}")
            return []

    def sync_once(self):
        """Perform a single synchronization loop."""
        cpu_data = self.fetch_cpu_usage()
        mem_data = self.fetch_memory_usage()

        # Update TopologyGraph with CPU data
        for result in cpu_data:
            pod_name = result['metric'].get('pod')
            if pod_name:
                cpu_val = float(result['value'][1])
                self.topology_graph.update_node(pod_name, "pod", {"cpu_usage": cpu_val})

        # Update TopologyGraph with Memory data
        for result in mem_data:
            pod_name = result['metric'].get('pod')
            if pod_name:
                mem_val = float(result['value'][1])
                # We do a partial update here, appending to existing state
                existing_state = dict(self.topology_graph.get_node_state(pod_name))
                existing_state.pop("type", None)
                existing_state["memory_usage"] = mem_val
                self.topology_graph.update_node(pod_name, "pod", existing_state)

    def start_sync_loop(self, interval_seconds: int = 15):
        """Continuously sync state in a background loop (blocking)."""
        logger.info("Starting State Synchronizer loop...")
        while True:
            self.sync_once()
            time.sleep(interval_seconds)
