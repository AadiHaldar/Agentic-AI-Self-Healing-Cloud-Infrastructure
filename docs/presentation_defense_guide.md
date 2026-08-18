# 🎓 Agentic AI Platform — Professor Presentation & Defense Guide

**Project Title:** Agentic AI — Self-Healing Cloud Infrastructure & Autonomous PR Review Platform  
**Live Cloud Dashboard:** [https://pr-review-agent.wonderfulflower-41d6d2a5.eastasia.azurecontainerapps.io](https://pr-review-agent.wonderfulflower-41d6d2a5.eastasia.azurecontainerapps.io)  
**GitHub Repository:** [https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure)

---

## 📑 Table of Contents
1. [Executive Summary & Core Novelty](#1-executive-summary--core-novelty)
2. [Mathematical Foundations & Formulas](#2-mathematical-foundations--formulas)
   - [A. SimiFed Cosine Similarity (Base Paper)](#a-simifed-cosine-similarity-base-paper)
   - [B. KernelSHAP Feature Attribution](#b-kernelshap-feature-attribution)
   - [C. SimPy Discrete-Event Queuing Model ($M/M/c$)](#c-simpy-discrete-event-queuing-model-mmc)
   - [D. Cloud Availability & MTTR Metric](#d-cloud-availability--mttr-metric)
3. [Codebase Architecture & File Mapping](#3-codebase-architecture--file-mapping)
4. [Step-by-Step Live Demo Script](#4-step-by-step-live-demo-script)
5. [Benchmarked Latency Metrics](#5-benchmarked-latency-metrics)
6. [Professor Defense Q&A (Top 10 Questions)](#6-professor-defense-qa-top-10-questions)

---

## 1. Executive Summary & Core Novelty

Modern cloud systems suffer from two disconnected vulnerabilities:
1. **Shift-Left Vulnerability (Pre-deployment):** Manual PR reviews take 24–48 hours; security vulnerabilities (SQL injection, hardcoded secrets, thread leaks) slip past review into production.
2. **Shift-Right Vulnerability (Runtime):** Standard autoscalers (Kubernetes HPA) react 3–5 minutes after CPU breaches 80%, triggering blunt restarts that cause cascading microservice failures without root cause diagnosis.

### 🌟 Our Platform's Solution (Dual-Engine Architecture)
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AGENTIC AI PLATFORM                                  │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│       PRODUCT A: PREVENTATIVE PR REVIEW   │       PRODUCT B: RUNTIME SELF-HEALING      │
│  • Multi-Tool AST Security & Linter Scan  │  • Real-Time Isolation Forest + XGBoost    │
│  • Gemini 3.6 Flash Code Logic Review     │  • KernelSHAP Mathematical Attribution     │
│  • AST Test Gap Detection (Flag-Only)     │  • SimPy Digital Twin 0.01s Dry-Run Gate   │
│  • Automated Fix PRs & Inline Suggestions │  • Parallel SimiFed RL vs. Gemini ReAct    │
│  • Quality Gate Check Runs (Merge Blocker)│  • Hardened Kubernetes & AKS Remediation   │
│  • Interactive @review-bot Conversational │  • Single-Pane-of-Glass React Control Plane│
└───────────────────────────────────────────┴────────────────────────────────────────────┘
```

---

## 2. Mathematical Foundations & Formulas

### A. SimiFed Cosine Similarity (Base Paper)
* **Academic Reference:** Deepika Saxena & Ashutosh Kumar Singh, *"A Self-Healing and Fault-Tolerant Cloud-based Digital Twin Processing Management Model"*, *IEEE Transactions on Industrial Informatics*, 2025 (`arXiv:2505.01215v1`).
* **Code Location:** [`agentic_engine/rl_agent.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/agentic_engine/rl_agent.py)

$$\text{Cosine}(R_i, R_j) = \frac{R_i \cdot R_j}{\|R_i\| \|R_j\|} = \frac{\sum_{k=1}^{n} R_{i,k} R_{j,k}}{\sqrt{\sum_{k=1}^{n} R_{i,k}^2} \sqrt{\sum_{k=1}^{n} R_{j,k}^2}}$$

* **Application:** Telemetry incident vectors $R = [\text{CPU}, \text{RAM}, \text{Latency}, \text{Request Rate}]$ are matched against pre-trained failure state-action matrices in **3.1 ms** to select optimal heuristic remediation (`SCALE_UP`, `RESTART_POD`, `PATCH_LIMITS`).

---

### B. KernelSHAP Feature Attribution
* **Academic Reference:** Scott M. Lundberg & Su-In Lee, *"A Unified Approach to Interpreting Model Predictions"*, *NeurIPS*, 2017.
* **Code Location:** [`detection/explainer/shap_explainer.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/detection/explainer/shap_explainer.py)

$$\phi_i(x) = \sum_{S \subseteq F \setminus \{i\}} \frac{|S|!(|F| - |S| - 1)!}{|F|!} \left[ f(S \cup \{i\}) - f(S) \right]$$

* **Where:**
  * $F$ = Complete set of telemetry features ($\text{CPU}, \text{RAM}, \text{Latency}, \text{Request Rate}$).
  * $S$ = Subset of features excluding feature $i$.
  * $f(S)$ = Anomaly score prediction of the Isolation Forest over feature subset $S$.
  * $\phi_i(x)$ = Shapley marginal attribution of feature $i$.
* **Application:** Explains *why* the anomaly occurred with exact values (`cpu_usage: +0.820`, `request_rate: +0.065`) removing black-box ambiguity.

---

### C. SimPy Discrete-Event Queuing Model ($M/M/c$)
* **Theory:** Multi-Server Discrete-Event Queuing Network.
* **Code Location:** [`digital_twin/simpy_engine.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/digital_twin/simpy_engine.py)

$$\rho = \frac{\lambda}{c \cdot \mu}$$

* **Where:**
  * $\lambda$ = Request arrival rate to the microservice (requests/sec).
  * $\mu$ = Processing service rate per container pod replica.
  * $c$ = Number of container replicas.
  * $\rho$ = Traffic intensity / utilization factor (must satisfy $\rho < 1.0$ for stability).
* **Application:** Simulates scaling replicas from $c=1$ to $c=4$ in **0.01 seconds**, predicting that peak CPU drops to **42.0%** before executing live Kubernetes commands.

---

### D. Cloud Availability & MTTR Metric
* **Formula:**
$$A = \frac{\text{MTBF}}{\text{MTBF} + \text{MTTR}}$$
* **Application:** By reducing Mean Time To Remediate ($\text{MTTR}$) from **300 seconds** (standard human/HPA) to **2.66 seconds** (autonomous dual-agent), system availability increases from $99.9\%$ to $99.999\%$ (Five Nines).

---

## 3. Codebase Architecture & File Mapping

| Subsystem | File Path | Core Function / Responsibility |
|---|---|---|
| **PR Review Pipeline** | [`pr_review_agent/pipeline.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/pr_review_agent/pipeline.py) | 11-stage review engine, diff chunking, Gemini 3.6 review, Check Run publisher |
| **Interactive Chat** | [`pr_review_agent/chat_handler.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/pr_review_agent/chat_handler.py) | `@review-bot` commands (`/add-docstrings`, `/dismiss`, `/re-review`, Q&A) |
| **GitHub App Auth** | [`pr_review_agent/github_app_auth.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/pr_review_agent/github_app_auth.py) | RS256 JWT generation, installation access token exchange |
| **Webhooks & FastApi** | [`pr_review_agent/webhook_handler.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/pr_review_agent/webhook_handler.py) | HMAC-SHA256 receiver, rate limiting, idempotency locks |
| **Digital Twin SimPy** | [`digital_twin/simpy_engine.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/digital_twin/simpy_engine.py) | 0.01s $M/M/c$ queuing simulation safety gate |
| **Topology DAG** | [`digital_twin/topology_graph.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/digital_twin/topology_graph.py) | NetworkX live Directed Acyclic Graph of microservices |
| **SHAP Explainer** | [`detection/explainer/shap_explainer.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/detection/explainer/shap_explainer.py) | KernelSHAP marginal feature importance attribution |
| **SimiFed RL Agent** | [`agentic_engine/rl_agent.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/agentic_engine/rl_agent.py) | Cosine similarity incident vector matching (3.1 ms reflex) |
| **Gemini ReAct Agent**| [`agentic_engine/llm_agent.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/agentic_engine/llm_agent.py) | Gemini Chain-of-Thought reasoning + tool calling |
| **Parallel Arbiter** | [`agentic_engine/orchestrator.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/agentic_engine/orchestrator.py) | Consensus arbitration between RL and LLM agents |

---

## 4. Step-by-Step Live Demo Script

### 🟢 Step 1: Open PowerShell & Create Demo Branch
```powershell
cd "c:\Users\aadih\Desktop\desktop\work\College\Semester 5\Cloud Computing\Project"

# Switch to branch and inject demo code
git checkout -b demo/live-pr-review

@'
# services/billing_service.py
import sqlite3

# CRITICAL SECURITY FLAW: Hardcoded API Secret Token
STRIPE_SECRET_KEY = "sk_live_prod_secret_token_9938472918471928374"

def process_customer_billing(customer_id: str, amount: float, card_number: str):
    # FLAW: Missing docstring & AST test gap
    db_conn = sqlite3.connect("billing.db")
    cursor = db_conn.cursor()

    # CRITICAL SECURITY FLAW: SQL Injection via raw string formatting
    sql_query = f"SELECT credit_limit FROM accounts WHERE customer_id = '{customer_id}'"
    cursor.execute(sql_query)
    
    account = cursor.fetchone()
    if account and account[0] >= amount:
        cursor.execute(f"UPDATE accounts SET credit_limit = credit_limit - {amount} WHERE customer_id = '{customer_id}'")
        db_conn.commit()
        db_conn.close()
        return {"status": "SUCCESS", "amount": amount}
        
    db_conn.close()
    return {"status": "FAILED", "reason": "Insufficient credit"}
'@ | Out-File -FilePath "services/billing_service.py" -Encoding utf8

git add services/billing_service.py
git commit -m "feat(billing): implement customer billing processor"
git push -u origin demo/live-pr-review
```

### 🟢 Step 2: Open PR on GitHub & Show Findings
1. Go to GitHub repo → Click **`Compare & pull request`** → Click **`Create pull request`**.
2. **Show the Red Cross (`❌`):** Quality Gate blocked merge due to critical vulnerabilities.
3. **Show the 🛡️ Verification Matrix Table:** Embedded directly in the bot's review comment.
4. **Show Inline Suggestion:** Click **`Files changed`** tab to show the clickable **`Apply suggestion`** block.

### 🟢 Step 3: Interactive Chat (`@review-bot`)
In the PR comment box, type:
```text
@review-bot /add-docstrings
```
*Bot replies in seconds with complete Google-style formatted docstrings!*

### 🟢 Step 4: Show Live Azure Dashboard
Open: `https://pr-review-agent.wonderfulflower-41d6d2a5.eastasia.azurecontainerapps.io`
- **`Analyze` Tab:** Point to SHAP feature attribution bar chart and SimPy safety gate verdict (`SAFE_TO_EXECUTE`, 42% CPU).
- **`Infra Healing` Tab:** Show the live SVG topology graph and click **`Inject CPU Spike Alert`** to demonstrate live self-healing consensus.

---

## 5. Benchmarked Latency Metrics

| Metric / Layer | Measured Latency | Industry Standard | Improvement |
|---|:---:|:---:|:---:|
| **Mean Time To Detect (MTTD)** | **2.34 ms** | 15–30 seconds | **~10,000x faster** |
| **SimiFed RL Reflex Decision** | **3.10 ms** | 1–2 minutes | **~30,000x faster** |
| **SimPy Digital Twin Safety Gate** | **10.2 ms** | No dry-run (blind) | **Deterministic safety** |
| **Gemini 3.6 ReAct Reasoning** | **2.65 s** | Manual RCA (15–30 min) | **~500x faster** |
| **Mean Time To Remediate (MTTR)** | **2.66 s** | 3–5 minutes (HPA) | **~100x faster** |
| **Shift-Left PR Review Pipeline** | **14–18 s** | 24–48 hours (Human) | **~5,000x faster** |

---

## 6. Professor Defense Q&A (Top 10 Questions)

### Q1: "Why not just use standard Kubernetes Horizontal Pod Autoscaler (HPA)?"
> **Answer:** *"HPA is reactive, scalar, and blind. It only triggers after CPU breaches 80% for 3–5 minutes, cannot diagnose root cause (e.g. memory leak vs thread deadlock vs traffic surge), and cannot predict cascading failures on upstream dependencies. Our agent diagnoses root cause in 2.34 ms using SHAP, pre-simulates safety in SimPy in 0.01s, and remediates in 2.66 seconds."*

### Q2: "What prevents the LLM from hallucinating an unsafe scaling command?"
> **Answer:** *"The LLM has zero direct execution privileges. Its output is constrained to a typed JSON schema and must pass through our deterministic SimPy Digital Twin Safety Gate. If the simulation predicts failure or instability ($\rho \ge 1.0$), the action is rejected and flagged for human operator override."*

### Q3: "How does the SimiFed algorithm in your project work?"
> **Answer:** *"Based on Saxena & Singh (IEEE TII 2025), SimiFed computes the Cosine Similarity between the active 4D telemetry vector and historical incident vectors. This provides a sub-millisecond (3.1 ms) heuristic reflex that complements the deeper (2.65 s) Gemini ReAct reasoning agent."*

### Q4: "How does your system prevent duplicate webhook executions?"
> **Answer:** *"We implement RFC 2104 HMAC-SHA256 cryptographic verification combined with an SQLite-backed idempotency table (`webhook_deliveries`). Duplicate GitHub delivery UUIDs are dropped in constant time before invoking any pipeline logic."*

### Q5: "How is the GitHub App authenticated securely without long-lived tokens?"
> **Answer:** *"It uses RS256 asymmetric cryptography. The app signs short-lived JWT tokens (expiring in 9 minutes) with a private RSA key stored in environment/vault, exchanging them for temporary 1-hour installation tokens scoped strictly to installed repositories."*

### Q6: "What is AST Test Gap Detection, and why is it flag-only?"
> **Answer:** *"We use Python's built-in `ast` (Abstract Syntax Tree) module to parse newly added public functions and verify if corresponding test cases exist in `tests/`. It is strictly flag-only to prevent hallucinating fake or non-deterministic tests."*

### Q7: "What happens if the RL agent and the LLM agent disagree on an action?"
> **Answer:** *"Our Parallel Orchestrator acts as an arbiter. If actions match, it executes with high confidence. If they diverge, the proposed actions are independently evaluated against the SimPy Digital Twin simulation gate—the action that yields the lowest simulated latency and CPU utilization wins."*

### Q8: "How does the Mermaid Call Graph work?"
> **Answer:** *"When a PR modifies 3 or more files, our AST parser traverses the import dependency tree across modified modules and outputs valid Mermaid `graph LR` syntax directly into the GitHub review comment."*

### Q9: "Where is this system deployed in production?"
> **Answer:** *"It is deployed on Microsoft Azure Container Apps (`rg-agentic-app-prod`) running inside a managed container environment backed by Azure Container Registry (ACR) and Log Analytics."*

### Q10: "What is the difference between the inline suggestion and the auto-fix PR?"
> **Answer:** *"Single-line logic fixes (like SQL parameterization) are delivered as in-place 1-click GitHub suggestion blocks. High-risk security vulnerabilities (like hardcoded secret extraction) trigger an autonomous Auto-Fix branch (`autoreview/fix-*`) with its own PR for enterprise auditing."*
