import xgboost as xgb
import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class XGBoostIDS:
    """
    Intrusion Detection System using XGBoost.
    Classifies network traffic or system call patterns as normal or malicious.
    """
    def __init__(self, model_path: str = None):
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42
        )
        self.is_trained = False
        if model_path:
            try:
                self.model.load_model(model_path)
                self.is_trained = True
            except Exception as e:
                logger.error(f"Failed to load XGBoost model from {model_path}: {e}")

    def train(self, X_train: np.ndarray, y_train: np.ndarray, save_path: str = None):
        """
        Train the XGBoost classifier.
        y_train should be binary (0 = normal, 1 = malicious).
        """
        logger.info(f"Training XGBoost IDS on {len(X_train)} samples...")
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        if save_path:
            self.model.save_model(save_path)
            logger.info(f"Model saved to {save_path}")

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        """
        Predict binary labels for the input data.
        Returns array of 0s and 1s.
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet!")
        return self.model.predict(X_test)
    
    def predict_proba(self, X_test: np.ndarray) -> np.ndarray:
        """
        Predict probabilities for the input data.
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet!")
        return self.model.predict_proba(X_test)
