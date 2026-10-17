import os
import joblib
import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

class MetricsAnomalyDetector:
    """
    Uses Isolation Forest to detect anomalies in infrastructure metrics.
    Auto-trains on `datasets/healthy_telemetry.csv` if available.
    """
    def __init__(self, contamination: float = 0.05, model_path: str = None):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.is_trained = False
        self.train_mean = None
        self.train_std = None
        self.feature_names = ["cpu_usage", "memory_usage", "latency_ms", "request_rate"]

        if model_path and os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                self.is_trained = True
            except Exception as e:
                logger.error(f"Failed to load Isolation Forest model from {model_path}: {e}")

        if not self.is_trained:
            dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../datasets/healthy_telemetry.csv"))
            if os.path.exists(dataset_path):
                try:
                    df = pd.read_csv(dataset_path)
                    X_train = df[self.feature_names].values
                    self.train(X_train)
                except Exception as e:
                    logger.warning(f"Could not train Isolation Forest on dataset: {e}")

    # ── step-by-step maths of the anomaly score (for the demo) ───────────────
    @staticmethod
    def _avg_path_length(n) -> float:
        """c(n): average path length of an unsuccessful search in a binary search tree (Liu et al., 2008)."""
        n = float(n)
        if n <= 1:
            return 0.0
        if n == 2:
            return 1.0
        return 2.0 * (np.log(n - 1.0) + 0.5772156649015329) - 2.0 * (n - 1.0) / n

    def explain_score(self, x) -> dict:
        """
        Reproduce sklearn's score for one sample, step by step, and verify it against the library:
            h_t(x)  path length of x in tree t (depth + c(leaf size))
            E[h(x)] mean over trees,    c(n)  normaliser,    s = 2^(-E[h]/c(n))
            score_samples = -s,         decision = score_samples - offset_,    anomaly if decision < 0
        """
        X = np.asarray(x, dtype=np.float32).reshape(1, -1)
        m = self.model
        depths = []
        for tree, feats in zip(m.estimators_, m.estimators_features_):
            Xs = X[:, feats]
            leaf = tree.apply(Xs)
            depth = float(tree.decision_path(Xs).sum(axis=1)[0]) - 1.0 + self._avg_path_length(tree.tree_.n_node_samples[leaf][0])
            depths.append(depth)
        mean_depth = float(np.mean(depths))
        c_n = self._avg_path_length(m.max_samples_)
        s = float(2.0 ** (-mean_depth / c_n))
        score_samples = -s
        offset = float(m.offset_)
        decision = score_samples - offset
        library = float(m.decision_function(X)[0])
        out = {
            "n_trees": len(m.estimators_), "max_samples": int(m.max_samples_),
            "depth_min": float(min(depths)), "depth_max": float(max(depths)), "mean_depth": mean_depth,
            "c_n": float(c_n), "s": s, "score_samples": score_samples, "offset": offset, "contamination": float(m.contamination),
            "decision": decision, "library_decision": library, "matches_library": bool(abs(decision - library) < 1e-4),
            "anomaly": decision < 0,
        }
        # how far each feature is from the healthy training data (context only: the forest does not use z-scores)
        if getattr(self, "train_mean", None) is not None:
            vals = X[0].astype(float)
            out["features"] = [
                {"name": n, "value": float(v), "mean": float(mu), "std": float(sd), "z": float((v - mu) / sd) if sd else 0.0}
                for n, v, mu, sd in zip(self.feature_names, vals, self.train_mean, self.train_std)
            ]
        return out

    def train(self, X_train: np.ndarray, save_path: str = None):
        """Train Isolation Forest on baseline healthy dataset."""
        logger.info(f"[MetricsAnomalyDetector] Training Isolation Forest on {len(X_train)} samples...")
        self.model.fit(X_train)
        self.train_mean = np.mean(X_train, axis=0)
        self.train_std = np.std(X_train, axis=0)
        self.is_trained = True
        
        if save_path:
            joblib.dump(self.model, save_path)

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        """
        Predict if samples are anomalous. Returns 1 for normal, -1 for anomaly.
        Ensures 2D input array formatting.
        """
        if not self.is_trained:
            raise ValueError("Isolation Forest model is not trained yet!")
        
        X_arr = np.array(X_test, dtype=np.float32)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)
        return self.model.predict(X_arr)
