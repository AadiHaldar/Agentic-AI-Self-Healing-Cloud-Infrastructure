import numpy as np
import logging
from typing import Dict, Any, List
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class SimiFedRLAgent:
    """
    Reinforcement Learning & Cosine-Similarity Baseline Agent (SF-DTM paper).
    Computes node resource similarity using Cosine Distance and decides allocations/scaling
    via Q-learning / Heuristic rules without relying on LLMs.
    """
    def __init__(self, n_actions: int = 4, alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 0.1):
        self.n_actions = n_actions  # 0: Do Nothing, 1: Scale Up, 2: Restart Pod, 3: Patch Limit
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_table = {}  # State-Action Q-table

    def _discretize_state(self, cpu_usage: float, mem_usage: float, anomaly_score: float) -> str:
        """Discretize continuous metrics into discrete state keys."""
        cpu_bin = int(cpu_usage * 5)      # 0-5 bins
        mem_bin = int(mem_usage * 5)      # 0-5 bins
        anom_bin = 1 if anomaly_score < 0 else 0 # 1 if anomaly, 0 if normal
        return f"c{cpu_bin}_m{mem_bin}_a{anom_bin}"

    def compute_cosine_similarity(self, node_metrics_a: List[float], node_metrics_b: List[float]) -> float:
        """SF-DTM paper: Calculate cosine similarity between two node metric vectors."""
        vec_a = np.array(node_metrics_a).reshape(1, -1)
        vec_b = np.array(node_metrics_b).reshape(1, -1)
        return float(cosine_similarity(vec_a, vec_b)[0][0])

    def select_action(self, state_key: str) -> int:
        """Epsilon-greedy action selection."""
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.n_actions)

        if np.random.rand() < self.epsilon:
            return np.random.randint(self.n_actions)
        else:
            return int(np.argmax(self.q_table[state_key]))

    def decide_remediation(self, target_service: str, cpu_usage: float, mem_usage: float, is_anomaly: bool) -> Dict[str, Any]:
        """
        Evaluate current metrics and return a structured remediation decision.
        """
        anomaly_val = -1.0 if is_anomaly else 1.0
        state_key = self._discretize_state(cpu_usage, mem_usage, anomaly_val)
        action_idx = self.select_action(state_key)

        actions = ["DO_NOTHING", "SCALE_UP", "RESTART_POD", "PATCH_LIMITS"]
        chosen_action = actions[action_idx]

        logger.info(f"[RL Agent] State: {state_key} | Chosen Action: {chosen_action} for {target_service}")

        return {
            "agent_type": "RL_SimiFed",
            "target": target_service,
            "action": chosen_action,
            "state": state_key,
            "confidence": 0.85 if not is_anomaly else 0.95,
            "rationale": f"SF-DTM Q-Table policy selection for state {state_key}"
        }

    def update_q_table(self, state_key: str, action: int, reward: float, next_state_key: str):
        """Update Q-table via Bellman equation."""
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.n_actions)
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = np.zeros(self.n_actions)

        best_next_action = np.argmax(self.q_table[next_state_key])
        td_target = reward + self.gamma * self.q_table[next_state_key][best_next_action]
        td_error = td_target - self.q_table[state_key][action]
        self.q_table[state_key][action] += self.alpha * td_error
