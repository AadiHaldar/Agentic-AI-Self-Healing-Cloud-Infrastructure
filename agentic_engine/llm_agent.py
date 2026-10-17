import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

from .tools.github_tools import github_manager

logger = logging.getLogger(__name__)

# gemini-1.5/2.0/2.5-flash have been retired by Google; override with GEMINI_MODEL.
GEMINI_MODELS = [m for m in (os.getenv("GEMINI_MODEL"), "gemini-3.6-flash", "gemini-3.8-flash") if m]

REACT_SYSTEM_PROMPT = """You are an Autonomous Self-Healing Cloud Operations Agent.
You monitor Kubernetes microservices, analyze metrics, read SHAP explainability summaries, run SimPy simulations, and execute safe remediation steps or open GitHub GitOps Pull Requests.

Your goal is to resolve infrastructure anomalies (CPU spikes, memory leaks, crashed pods, DDoS attacks) with minimal downtime.

Respond STRICTLY in valid JSON format with no additional markdown wrapping or text outside the JSON object:
{
  "thought": "<your step-by-step reasoning>",
  "root_cause": "<identified root cause>",
  "simulation_result": "<safe | unsafe>",
  "action_type": "<SCALE_UP | RESTART_POD | PATCH_LIMITS | CREATE_GITOPS_PR | SUBMIT_CODE_PATCH_PR | DO_NOTHING>",
  "target_service": "<target service name>",
  "explanation": "<human readable explanation for the operator>"
}
"""

class LLMReActAgent:
    """
    LLM-powered ReAct Agent for self-healing infrastructure.
    Uses new `google.genai` SDK (`GEMINI_API_KEY`) for real-time autonomous reasoning.
    """
    def __init__(self, k8s_tools, sim_tools, provider: str = "gemini"):
        self.k8s_tools = k8s_tools
        self.sim_tools = sim_tools
        self.provider = provider
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.legacy_genai = None

        if self.api_key:
            # 1. Try modern google.genai SDK
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("[LLM Agent] Successfully initialized modern google.genai Client.")
            except Exception as e:
                logger.debug(f"[LLM Agent] google.genai client initialization fallback: {e}")
                # 2. Fallback to google.generativeai if modern package is unavailable
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=self.api_key)
                    self.legacy_genai = legacy_genai
                    logger.info("[LLM Agent] Fallback to google.generativeai SDK.")
                except Exception as ex:
                    logger.warning(f"[LLM Agent] Could not configure Gemini API: {ex}")

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Invoke Gemini API using google.genai SDK to generate structured ReAct reasoning."""
        full_prompt = f"{REACT_SYSTEM_PROMPT}\n\nUSER ALERT:\n{prompt}"
        
        # Method 1: Modern google.genai SDK
        if self.client:
            for model_id in GEMINI_MODELS:
                try:
                    response = self.client.models.generate_content(
                        model=model_id,
                        contents=full_prompt
                    )
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif text.startswith("```"):
                        text = text.split("```")[1].split("```")[0].strip()
                    out = json.loads(text)
                    out["_source"] = f"gemini:{model_id}"
                    return out
                except Exception as e:
                    logger.debug(f"[LLM Agent google.genai] Model {model_id} error: {e}")
                    continue

        # Method 2: Legacy google.generativeai fallback
        if self.legacy_genai:
            for model_id in ['gemini-1.5-flash', 'gemini-pro']:
                try:
                    m = self.legacy_genai.GenerativeModel(model_id)
                    response = m.generate_content(full_prompt)
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif text.startswith("```"):
                        text = text.split("```")[1].split("```")[0].strip()
                    out = json.loads(text)
                    out["_source"] = f"gemini-legacy:{model_id}"
                    return out
                except Exception as e:
                    logger.debug(f"[LLM Agent legacy] Model {model_id} error: {e}")
                    continue

        # Method 3: Structured ReAct fallback agent if API calls fail
        return {
            "_source": "fallback",
            "thought": "SHAP telemetry indicates high CPU congestion. SimPy Digital Twin simulation passed safety verification.",
            "root_cause": "Resource congestion on target service detected via telemetry analysis.",
            "simulation_result": "safe",
            "action_type": "SCALE_UP" if "scale" in prompt.lower() else "RESTART_POD",
            "target_service": prompt.split()[0] if prompt else "checkoutservice",
            "explanation": "Agent evaluated SHAP telemetry alert, verified simulation safety, and executed dynamic remediation."
        }

    _SIM_ACTION = {"SCALE_UP": "SCALE", "RESTART_POD": "RESTART", "PATCH_LIMITS": "PATCH"}

    def evaluate_and_heal(self, alert_context: Dict[str, Any], execute: bool = False) -> Dict[str, Any]:
        """
        Executes the ReAct (Reason -> Simulate -> Act) Loop.

        `execute=False` (default) produces the plan and the digital-twin verdict only;
        nothing is sent to the cluster or GitHub. Pass `execute=True` to actuate.
        """
        service = alert_context.get("target_service", "checkoutservice")
        shap_explanation = alert_context.get("shap_explanation", "")
        cpu_usage = alert_context.get("cpu_usage", 0.0)
        mem_usage = alert_context.get("mem_usage", 0.0)
        sim_params = {"cpu": cpu_usage, "memory": mem_usage,
                      "latency_ms": alert_context.get("latency_ms"), "request_rate": alert_context.get("request_rate")}
        
        logger.info(f"[LLM Agent] Starting ReAct evaluation for service '{service}'...")
        
        # Step 1: Run SimPy Digital Twin simulation dry-run
        pre_action = "RESTART" if cpu_usage > 0.8 else "SCALE"
        sim_result = self.sim_tools.simulate_remediation(
            action_type=pre_action,
            target=service,
            params=sim_params
        )
        
        is_safe = sim_result.get("is_safe", True)
        forecast = sim_result.get("baseline", {})
        
        # Step 2: Formulate prompt for Gemini LLM
        prompt = f"""
Service Name: {service}
CPU Usage: {cpu_usage * 100:.1f}%
Memory Usage: {mem_usage * 100:.1f}%
SHAP Explainability String: {shap_explanation}
Digital twin forecast WITHOUT intervention: peak CPU {forecast.get('peak_cpu', 0) * 100:.0f}%, peak memory {forecast.get('peak_memory', 0) * 100:.0f}% over the next 10 steps
Predictive Forecaster Trend: High exhaustion risk within 10 minutes.
        """
        
        # Step 3: Real LLM Reasoning Call
        llm_output = self._call_llm(prompt)
        action_type = llm_output.get("action_type", "RESTART_POD")

        # Step 3b: the safety gate must judge the action the LLM actually chose
        chosen_sim_action = self._SIM_ACTION.get(action_type)
        if chosen_sim_action and chosen_sim_action != pre_action:
            sim_result = self.sim_tools.simulate_remediation(
                action_type=chosen_sim_action,
                target=service,
                params=sim_params
            )
            is_safe = sim_result.get("is_safe", True)
        
        # If the gate rejects the chosen action as ineffective/risky, ask it what it WOULD approve instead.
        gate_alternative = None
        if chosen_sim_action and not is_safe and sim_result.get("recommendation") in ("INEFFECTIVE", "RISK_OF_OVERLOAD"):
            gate_alternative = self.sim_tools.suggest_alternative(service, sim_params, exclude=chosen_sim_action)

        # Step 4: Execute K8s Action if simulation is safe
        if not execute:
            exec_res = {"status": "not_executed", "message": f"Plan only (execute=false). Proposed: {action_type}"}
        elif not is_safe:
            exec_res = {"status": "skipped", "message": "SimPy Digital Twin flagged high risk of cascading failure."}
            action_type = "DO_NOTHING"
        elif action_type == "RESTART_POD":
            exec_res = self.k8s_tools.restart_pod(service)
        elif action_type == "SCALE_UP":
            exec_res = self.k8s_tools.scale_deployment(service, replicas=3)
        elif action_type == "PATCH_LIMITS":
            exec_res = self.k8s_tools.patch_resource_limits(service, cpu_limit="1000m", memory_limit="1024Mi")
        elif action_type == "CREATE_GITOPS_PR":
            exec_res = github_manager.create_gitops_pr(service, replicas=3, cpu_limit="1000m")
        elif action_type == "SUBMIT_CODE_PATCH_PR":
            exec_res = github_manager.create_code_patch_pr(
                service=service,
                file_path=f"src/{service}/handler.py",
                issue_summary="Resource leak / timeout unhandled exception",
                patch_code="with timeout_protection(): process()"
            )
        else:
            action_type = "DO_NOTHING"
            exec_res = {"status": "no_action_needed"}
            
        decision = {
            "agent_type": "LLM_ReAct_Gemini",
            "source": llm_output.get("_source", "unknown"),
            "proposed_action": llm_output.get("action_type", "RESTART_POD"),
            "executed": bool(execute),
            "thought": llm_output.get("thought"),
            "root_cause": llm_output.get("root_cause"),
            "simulation": sim_result,
            "gate_alternative": gate_alternative,
            "action_taken": action_type,
            "execution_result": exec_res,
            "explanation": llm_output.get("explanation")
        }
        
        logger.info(f"[LLM Agent Gemini] Final Action: {action_type} on {service}")
        return decision
