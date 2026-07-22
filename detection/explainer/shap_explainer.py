import shap
import numpy as np
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class SHAPExplainer:
    """
    Wrapper around SHAP to explain model predictions for the LLM Agent.
    """
    def __init__(self, model: Any, background_data: np.ndarray, feature_names: List[str] = None):
        """
        Initializes the SHAP explainer.
        Uses TreeExplainer for tree-based models (like XGBoost) or KernelExplainer as fallback.
        """
        self.feature_names = feature_names
        
        # Determine the type of model and initialize appropriate SHAP explainer
        # A simple check for get_booster usually implies XGBoost
        if hasattr(model, 'get_booster'):
            logger.info("Initializing SHAP TreeExplainer for XGBoost model.")
            self.explainer = shap.TreeExplainer(model)
        else:
            logger.info("Initializing SHAP KernelExplainer for generic model.")
            # KernelExplainer requires a predict function
            predict_fn = getattr(model, "predict", None)
            if predict_fn is None:
                raise ValueError("Model must have a predict function to use KernelExplainer.")
            self.explainer = shap.KernelExplainer(predict_fn, background_data)
            
    def explain_instance(self, instance: np.ndarray) -> Dict[str, float]:
        """
        Calculates SHAP values for a single instance to explain the prediction.
        Returns a dictionary mapping feature names to their SHAP values (importance).
        """
        # Calculate SHAP values for the instance
        shap_values = self.explainer.shap_values(instance)
        
        # If it's a binary classification with TreeExplainer, shap_values might be a list
        if isinstance(shap_values, list):
            # Take the SHAP values for the positive class (usually index 1)
            shap_values = shap_values[1]
            
        # Ensure shap_values is a 1D array for the single instance
        if shap_values.ndim > 1:
            shap_values = shap_values[0]
            
        if self.feature_names and len(self.feature_names) == len(shap_values):
            # Map values to feature names
            return {name: float(val) for name, val in zip(self.feature_names, shap_values)}
        else:
            # Map values to feature indices if names are not provided or mismatch
            return {f"feature_{i}": float(val) for i, val in enumerate(shap_values)}

    def format_explanation_for_llm(self, shap_dict: Dict[str, float], top_k: int = 3) -> str:
        """
        Formats the top K most impactful features into a string for the LLM prompt.
        """
        # Sort features by absolute SHAP value (magnitude of impact)
        sorted_features = sorted(shap_dict.items(), key=lambda item: abs(item[1]), reverse=True)
        
        top_features = sorted_features[:top_k]
        explanation = "Key factors driving this prediction:\n"
        for feature, value in top_features:
            impact = "increased" if value > 0 else "decreased"
            explanation += f"- {feature} {impact} the risk score (impact: {value:.4f})\n"
            
        return explanation
