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

    def train(self, X_train: np.ndarray, save_path: str = None):
        """Train Isolation Forest on baseline healthy dataset."""
        logger.info(f"[MetricsAnomalyDetector] Training Isolation Forest on {len(X_train)} samples...")
        self.model.fit(X_train)
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
