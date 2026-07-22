from sklearn.ensemble import IsolationForest
import numpy as np
import logging
import joblib

logger = logging.getLogger(__name__)

class MetricsAnomalyDetector:
    """
    Uses Isolation Forest to detect anomalies in infrastructure metrics
    (e.g., CPU, Memory spikes indicating resource exhaustion or bugs).
    """
    def __init__(self, contamination: float = 0.05, model_path: str = None):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.is_trained = False
        if model_path:
            try:
                self.model = joblib.load(model_path)
                self.is_trained = True
            except Exception as e:
                logger.error(f"Failed to load Isolation Forest from {model_path}: {e}")

    def train(self, X_train: np.ndarray, save_path: str = None):
        """
        Train the Isolation Forest on a baseline (healthy) dataset.
        X_train should be shape (n_samples, n_features).
        """
        logger.info(f"Training Isolation Forest on {len(X_train)} samples...")
        self.model.fit(X_train)
        self.is_trained = True
        
        if save_path:
            joblib.dump(self.model, save_path)
            logger.info(f"Model saved to {save_path}")

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        """
        Predict if samples are anomalous.
        Returns 1 for normal, -1 for anomaly.
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet!")
        return self.model.predict(X_test)
