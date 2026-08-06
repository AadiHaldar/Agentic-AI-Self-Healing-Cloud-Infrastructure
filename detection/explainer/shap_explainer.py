import shap
import numpy as np
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class SHAPExplainer:
    """
    Wrapper around SHAP to explain model predictions for the LLM Agent.
    Supports TreeExplainer (XGBoost) and KernelExplainer (IsolationForest).
    """
    def __init__(self, model: Any, background_data: np.ndarray = None, feature_names: List[str] = None):
        self.feature_names = feature_names or ["cpu_usage", "memory_usage", "latency_ms", "request_rate"]
        
        if background_data is None:
            background_data = np.random.normal(loc=[0.25, 0.40, 45.0, 120.0], scale=[0.05, 0.08, 5.0, 15.0], size=(20, 4))
            
        if hasattr(model, 'get_booster'):
            logger.info("[SHAPExplainer] Initializing TreeExplainer for XGBoost model.")
            self.explainer = shap.TreeExplainer(model)
        else:
            logger.info("[SHAPExplainer] Initializing KernelExplainer for IsolationForest model.")
            predict_fn = getattr(model, "predict", None) or getattr(model, "decision_function", None)
            self.explainer = shap.KernelExplainer(predict_fn, background_data)
            
    def explain_instance(self, instance: np.ndarray) -> Dict[str, float]:
        """Calculates SHAP feature values for a single metric vector instance."""
        inst_arr = np.array(instance, dtype=np.float32)
        if inst_arr.ndim == 1:
            inst_arr = inst_arr.reshape(1, -1)
            
        try:
            shap_values = self.explainer.shap_values(inst_arr)
            if isinstance(shap_values, list):
                shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
            if shap_values.ndim > 1:
                shap_values = shap_values[0]
                
            return {name: float(val) for name, val in zip(self.feature_names, shap_values)}
        except Exception as e:
            logger.warning(f"[SHAPExplainer] Computation fallback: {e}")
            # Fallback relative weighting calculation if SHAP kernel fails
            raw_vals = inst_arr[0]
            total = sum(abs(v) for v in raw_vals) or 1.0
            return {name: float(val / total) for name, val in zip(self.feature_names, raw_vals)}

    def format_explanation_for_llm(self, shap_dict: Dict[str, float], top_k: int = 3) -> str:
        """Formats the top K most impactful features into an English string for the LLM prompt."""
        sorted_features = sorted(shap_dict.items(), key=lambda item: abs(item[1]), reverse=True)
        top_features = sorted_features[:top_k]
        explanation = "SHAP Feature Attribution Analysis:\n"
        for feature, value in top_features:
            impact = "increased" if value > 0 else "decreased"
            explanation += f"- {feature} {impact} anomaly risk score by {abs(value):.4f}\n"
        return explanation
