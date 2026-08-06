import numpy as np
import logging
from typing import Dict, Any, List
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class SimiFedRLAgent:
    """
    Reinforcement Learning & Cosine-Similarity Baseline Agent (SF-DTM paper).
    Computes node resource similarity using Cosine Distance and decides allocations/scaling
    via Q-learning policy discretization.
    """
    def __init__(self, n_actions: int = 4, alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 0.1):
        self.n_actions = n_actions  # 0: DO_NOTHING, 1: SCALE_UP, 2: RESTART_POD, 3: PATCH_LIMITS
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_table = {}
        
        # Reference baseline node vector for cosine similarity computation
        self.healthy_node_baseline = np.array([0.25, 0.40, 45.0, 120.0])

    def compute_cosine_similarity(self, current_metrics: List[float]) -> float:
        """SF-DTM paper algorithm: Calculate cosine similarity between node metric vectors."""
        vec_a = np.array(current_metrics).reshape(1, -1)
        vec_b = self.healthy_node_baseline.reshape(1, -1)
        sim = cosine_similarity(vec_a, vec_b)[0][0]
        return float(sim)

    def _discretize_state(self, cpu_usage: float, mem_usage: float, is_anomaly: bool) -> str:
        """Discretize state space combining metrics and SF-DTM cosine similarity."""
        cos_sim = self.compute_cosine_similarity([cpu_usage, mem_usage, cpu_usage * 100, mem_usage * 200])
        sim_bin = int(cos_sim * 4)  # 0-4 similarity bin
        cpu_bin = min(5, int(cpu_usage * 5))
        anom_bin = 1 if is_anomaly else 0
        return f"sim{sim_bin}_c{cpu_bin}_a{anom_bin}"

    def select_action(self, state_key: str) -> int:
        """Epsilon-greedy action selection."""
        if state_key not in self.q_table:
            # Seed heuristic initial values so agent doesn't do nothing on anomalies
            self.q_table[state_key] = np.array([0.1, 0.8, 0.9, 0.7]) if "a1" in state_key else np.array([0.9, 0.1, 0.1, 0.1])

        if np.random.rand() < self.epsilon:
            return np.random.randint(self.n_actions)
        else:
            return int(np.argmax(self.q_table[state_key]))

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

    def decide_remediation(self, target_service: str, cpu_usage: float, mem_usage: float, is_anomaly: bool) -> Dict[str, Any]:
        """Evaluate current metrics and return structured remediation decision."""
        state_key = self._discretize_state(cpu_usage, mem_usage, is_anomaly)
        action_idx = self.select_action(state_key)

        actions = ["DO_NOTHING", "SCALE_UP", "RESTART_POD", "PATCH_LIMITS"]
        chosen_action = actions[action_idx]
        cos_sim = self.compute_cosine_similarity([cpu_usage, mem_usage, cpu_usage * 100, mem_usage * 200])

        # Online update reward calculation
        reward = -1.0 if (is_anomaly and chosen_action == "DO_NOTHING") else 1.0
        self.update_q_table(state_key, action_idx, reward, state_key)

        logger.info(f"[RL Agent SF-DTM] State: {state_key} (Cosine Sim: {cos_sim:.3f}) | Chosen Action: {chosen_action}")

        return {
            "agent_type": "RL_SimiFed",
            "target": target_service,
            "action": chosen_action,
            "state": state_key,
            "cosine_similarity": round(cos_sim, 4),
            "confidence": 0.92 if is_anomaly else 0.98,
            "rationale": f"SF-DTM Q-Table policy selection (Cosine Similarity to baseline: {cos_sim:.3f})"
        }
