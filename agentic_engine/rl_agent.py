import json
import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from . import rl_training

logger = logging.getLogger(__name__)

HEALTHY_LATENCY_MS = 45.0
HEALTHY_REQUEST_RATE = 120.0


class SimiFedRLAgent:
    """
    Tabular Q-learning remediation policy (with the SF-DTM cosine-similarity feature reported alongside).

    The Q-table is trained OFFLINE against a fault-dynamics simulator (see agentic_engine/rl_training.py and
    docs/rl_training_report.md) and is frozen at inference: it acts greedily by default (epsilon = 0), and it
    does not learn online. If no trained table is found it falls back to a hand-set prior, and says so in
    `policy_source`. It is not validated on a real cluster.
    """
    ACTIONS = rl_training.ACTIONS  # 0: DO_NOTHING, 1: SCALE_UP, 2: RESTART_POD, 3: PATCH_LIMITS

    def __init__(self, n_actions: int = 4, alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 0.0,
                 model_path: Optional[str] = None):
        self.n_actions = n_actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_table: Dict[str, np.ndarray] = {}
        self.policy_source = "prior (no trained table found)"

        # Reference baseline node vector for cosine similarity computation
        self.healthy_node_baseline = np.array([0.25, 0.40, 45.0, 120.0])

        path = model_path or rl_training.MODEL_PATH
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    blob = json.load(fh)
                self.q_table = {k: np.array(v, dtype=float) for k, v in blob["q"].items()}
                self.policy_source = f"trained offline on a fault simulator ({blob.get('episodes', '?'):,} episodes)"
            except Exception as e:
                logger.warning("[RL Agent] Could not load %s: %s", path, e)

    def compute_cosine_similarity(self, current_metrics: List[float]) -> float:
        """SF-DTM paper algorithm: Calculate cosine similarity between node metric vectors."""
        vec_a = np.array(current_metrics).reshape(1, -1)
        vec_b = self.healthy_node_baseline.reshape(1, -1)
        sim = cosine_similarity(vec_a, vec_b)[0][0]
        return float(sim)

    @staticmethod
    def _features(cpu_usage, mem_usage, latency_ms, request_rate):
        lat = HEALTHY_LATENCY_MS if latency_ms is None else latency_ms
        rate = HEALTHY_REQUEST_RATE if request_rate is None else request_rate
        return cpu_usage, mem_usage, lat, rate

    def _discretize_state(self, cpu_usage: float, mem_usage: float, is_anomaly: bool,
                          latency_ms: float = None, request_rate: float = None) -> str:
        """State = CPU, memory, latency and request-rate buckets plus the anomaly-detector flag.
        Missing latency / request rate default to healthy-baseline values."""
        cpu, mem, lat, rate = self._features(cpu_usage, mem_usage, latency_ms, request_rate)
        return rl_training.state_key(cpu, mem, lat, rate, bool(is_anomaly))

    def _cosine(self, cpu_usage, mem_usage, latency_ms=None, request_rate=None) -> float:
        return self.compute_cosine_similarity(list(self._features(cpu_usage, mem_usage, latency_ms, request_rate)))

    def _prior(self, state_key: str) -> np.ndarray:
        return np.array([0.1, 0.8, 0.9, 0.7]) if state_key.endswith("a1") else np.array([0.9, 0.1, 0.1, 0.1])

    def select_action(self, state_key: str) -> int:
        """Greedy action from the Q-table (epsilon-greedy only if epsilon > 0)."""
        if state_key not in self.q_table:
            self.q_table[state_key] = self._prior(state_key)  # unseen state: fall back to the prior
        if self.epsilon > 0 and np.random.rand() < self.epsilon:
            return int(np.random.randint(self.n_actions))
        return int(np.argmax(self.q_table[state_key]))

    def update_q_table(self, state_key: str, action: int, reward: float, next_state_key: Optional[str] = None):
        """Q-learning update (next_state_key=None means a terminal / single-step decision)."""
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.n_actions)
        target = reward
        if next_state_key is not None:
            if next_state_key not in self.q_table:
                self.q_table[next_state_key] = np.zeros(self.n_actions)
            target += self.gamma * float(np.max(self.q_table[next_state_key]))
        self.q_table[state_key][action] += self.alpha * (target - self.q_table[state_key][action])

    def decide_remediation(self, target_service: str, cpu_usage: float, mem_usage: float, is_anomaly: bool,
                           latency_ms: float = None, request_rate: float = None) -> Dict[str, Any]:
        """Evaluate current metrics and return a structured remediation decision (no online learning)."""
        state_key = self._discretize_state(cpu_usage, mem_usage, is_anomaly, latency_ms, request_rate)
        action_idx = self.select_action(state_key)
        chosen_action = self.ACTIONS[action_idx]
        cos_sim = self._cosine(cpu_usage, mem_usage, latency_ms, request_rate)
        q = self.q_table.get(state_key)
        logger.info(f"[RL Agent] State: {state_key} | Chosen Action: {chosen_action}")

        return {
            "agent_type": "RL_SimiFed",
            "target": target_service,
            "action": chosen_action,
            "state": state_key,
            "cosine_similarity": round(cos_sim, 4),
            "q_values": {a: round(float(q[i]), 3) for i, a in enumerate(self.ACTIONS)} if q is not None else None,
            "policy": self.policy_source,
            "rationale": f"Greedy Q-table action; {self.policy_source}. Cosine similarity to the healthy baseline: {cos_sim:.3f}.",
        }
