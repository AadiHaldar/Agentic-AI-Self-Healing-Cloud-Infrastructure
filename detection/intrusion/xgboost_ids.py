import os
import xgboost as xgb
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class XGBoostIDS:
    """
    Intrusion Detection System using XGBoost.
    Classifies network traffic or system call patterns as normal or malicious.
    Auto-trains on `datasets/ids_traffic.csv` if available.
    """
    def __init__(self, model_path: str = None):
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            eval_metric='logloss',
            random_state=42
        )
        self.is_trained = False
        self.feature_names = ["packet_count", "byte_rate", "syn_flag_count", "error_rate"]

        if model_path and os.path.exists(model_path):
            try:
                self.model.load_model(model_path)
                self.is_trained = True
            except Exception as e:
                logger.error(f"Failed to load XGBoost model from {model_path}: {e}")

        if not self.is_trained:
            dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../datasets/ids_traffic.csv"))
            if os.path.exists(dataset_path):
                try:
                    df = pd.read_csv(dataset_path)
                    X_train = df[self.feature_names].values
                    y_train = df["is_malicious"].values
                    self.train(X_train, y_train)
                except Exception as e:
                    logger.warning(f"Could not train XGBoost IDS on dataset: {e}")

    def train(self, X_train: np.ndarray, y_train: np.ndarray, save_path: str = None):
        """Train XGBoost IDS model."""
        logger.info(f"[XGBoostIDS] Training XGBoost IDS on {len(X_train)} samples...")
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        if save_path:
            self.model.save_model(save_path)

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        """Predict binary labels (0 = normal, 1 = malicious)."""
        if not self.is_trained:
            raise ValueError("XGBoost IDS model is not trained yet!")
        X_arr = np.array(X_test, dtype=np.float32)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)
        return self.model.predict(X_arr)
    
    def predict_proba(self, X_test: np.ndarray) -> np.ndarray:
        """Predict probability scores."""
        if not self.is_trained:
            raise ValueError("XGBoost IDS model is not trained yet!")
        X_arr = np.array(X_test, dtype=np.float32)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)
        return self.model.predict_proba(X_arr)
