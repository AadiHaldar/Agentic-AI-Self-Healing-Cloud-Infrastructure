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
            background_data = self._default_background()
            
        if hasattr(model, 'get_booster'):
            logger.info("[SHAPExplainer] Initializing TreeExplainer for XGBoost model.")
            self.explainer = shap.TreeExplainer(model)
        else:
            logger.info("[SHAPExplainer] Initializing KernelExplainer for IsolationForest model.")
            if hasattr(model, "decision_function"):
                # decision_function is high for normal points; negate it so a POSITIVE SHAP
                # value always means "pushes toward anomaly". (predict() is a +/-1 step function.)
                predict_fn = lambda X: -model.decision_function(X)  # noqa: E731
            else:
                predict_fn = getattr(model, "predict", None)
            self.explainer = shap.KernelExplainer(predict_fn, background_data)
            self.predict_fn = predict_fn
            self.background_size = int(len(background_data))
            
    @staticmethod
    def _default_background() -> np.ndarray:
        """Sample of the healthy training telemetry if present, else a synthetic healthy cloud."""
        import os
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../datasets/healthy_telemetry.csv"))
        try:
            import pandas as pd
            df = pd.read_csv(path)
            return df[["cpu_usage", "memory_usage", "latency_ms", "request_rate"]].sample(50, random_state=42).values
        except Exception:
            return np.random.normal(loc=[0.25, 0.40, 45.0, 120.0], scale=[0.05, 0.08, 5.0, 15.0], size=(50, 4))

    def explain_math(self, instance: np.ndarray, shap_dict: Dict[str, float]) -> Dict[str, Any]:
        """Numbers needed to show KernelSHAP step by step: base value, f(x), kernel weights and the additivity check."""
        from math import comb
        inst = np.array(instance, dtype=np.float32).reshape(1, -1)
        fn = getattr(self, "predict_fn", None)
        fx = float(np.ravel(fn(inst))[0]) if fn else None
        base = float(np.ravel(self.explainer.expected_value)[0])
        m = len(self.feature_names)
        weights = {k: (m - 1) / (comb(m, k) * k * (m - k)) for k in range(1, m)}
        total = float(sum(shap_dict.values()))
        return {
            "base_value": base, "fx": fx, "phi": dict(shap_dict), "sum_phi": total,
            "reconstructed": base + total, "gap": None if fx is None else abs(base + total - fx),
            "n_features": m, "kernel_weights": weights, "background_size": getattr(self, "background_size", None),
            "output": "anomaly score = -decision_function (higher = more anomalous)",
        }

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
