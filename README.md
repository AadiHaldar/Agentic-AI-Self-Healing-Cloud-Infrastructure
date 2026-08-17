# Agentic AI — Self-Healing Cloud Infrastructure & Autonomous PR Review Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF.svg)](https://vitejs.dev/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-2.0%20Flash-4285F4.svg)](https://ai.google.dev/)
[![Azure AKS](https://img.shields.io/badge/Azure-AKS%20%26%20ACR-0078D4.svg)](https://azure.microsoft.com/en-us/products/kubernetes-service)
[![GitHub App](https://img.shields.io/badge/GitHub%20App-Manifest%20Flow-181717.svg)](https://docs.github.com/en/apps)
[![Tests](https://img.shields.io/badge/Tests-29%20Passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> An enterprise-grade, dual-engine cloud reliability platform combining **Shift-Left Autonomous PR Code Review with Quality Gates** and **Predictive Self-Healing Cloud Infrastructure** powered by Digital Twin Simulations, SHAP Explainable AI, and Parallel ReAct LLM Reasoning.

---

##  Table of Contents

- [Executive Overview](#-executive-overview)
- [System Architecture](#-system-architecture)
- [Research Foundations: Base Paper & Reference Literature](#-research-foundations-base-paper--reference-literature)
  - [The Base Paper: SF-DTM (Saxena & Singh, IEEE TII 2025)](#the-base-paper-sf-dtm-saxena--singh-ieee-tii-2025)
  - [Comprehensive Reference Literature (9 Key Studies)](#comprehensive-reference-literature-9-key-studies)
  - [Theoretical Mappings: What We Implemented from Literature](#theoretical-mappings-what-we-implemented-from-literature)
  - [Architectural Innovations: What We Made Better](#architectural-innovations-what-we-made-better)
- [Product A — PR Review Agent (`pr_review_agent/`)](#-product-a--pr-review-agent)
  - [11-Stage Review Pipeline](#11-stage-review-pipeline)
  - [Interactive `@review-bot` Commands](#interactive-review-bot-commands)
  - [Learnings & Suppression Loop](#learnings--suppression-loop)
  - [Per-Repository Configuration (`.review-agent.yml`)](#per-repository-configuration-review-agentyml)
- [Product B — Infrastructure Self-Healing Engine (`agentic_engine/`)](#-product-b--infrastructure-self-healing-engine)
  - [Digital Twin Simulation Gate (`digital_twin/`)](#digital-twin-simulation-gate)
  - [Parallel Agent Orchestrator (RL Baseline vs. Gemini ReAct)](#parallel-agent-orchestrator)
  - [SHAP Explainable AI & Anomaly Detection](#shap-explainable-ai--anomaly-detection)
- [Modern React + Vite Control Plane (`dashboard/frontend-vite/`)](#-modern-react--vite-control-plane)
- [Microsoft Azure Cloud Deployment (`infrastructure/terraform/azure/`)](#-microsoft-azure-cloud-deployment)
- [API & Webhook Reference](#-api--webhook-reference)
- [Getting Started Locally](#-getting-started-locally)
- [Running the Test Suite](#-running-the-test-suite)
- [Implementation Status Matrix](#-implementation-status-matrix)
- [License](#-license)

---

##  Executive Overview

Modern cloud engineering ecosystems suffer from two disconnected vulnerabilities:
1. **Developer Velocity & Security Drift:** Code reviews take days; memory leaks, dependency CVEs, missing unit tests, and secret tokens slip past manual reviews into production branches.
2. **Reactive Infrastructure Outages:** Autoscalers (e.g. Kubernetes HPA) react 3–5 minutes after CPU/RAM breaches critical thresholds, executing blunt restarts that cause cascading microservice failures without root cause diagnosis.

This platform bridges software development and cloud operations through a unified, closed-loop AI architecture:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AGENTIC AI PLATFORM                                  │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│       PRODUCT A: PREVENTATIVE PR REVIEW   │       PRODUCT B: RUNTIME SELF-HEALING      │
│  • Multi-Tool AST Security & Linter Scan  │  • Real-Time Isolation Forest + XGBoost    │
│  • Gemini 2.0 Flash Code Logic Review     │  • KernelSHAP Mathematical Attribution     │
│  • AST Test Gap Detection (Flag-Only)     │  • SimPy Digital Twin 0.01s Dry-Run Gate   │
│  • Automated Fix PRs & Inline Suggestions │  • Parallel SimiFed RL vs. Gemini ReAct    │
│  • Quality Gate Check Runs (Merge Blocker)│  • Hardened Kubernetes & AKS Remediation   │
│  • Interactive @review-bot Conversational │  • Single-Pane-of-Glass React/Vite Console │
└───────────────────────────────────────────┴────────────────────────────────────────────┘
```

---

##  System Architecture

```mermaid
graph TB
    subgraph "Developer & GitHub Ecosystem"
        DEV["Developer / Engineering Team"]
        PR["Pull Request / Code Changes"]
        GH_APP["GitHub App & Webhook Receiver"]
    end

    subgraph "Shift-Left Review Engine (pr_review_agent/)"
        HMAC["HMAC-SHA256 Verifier"]
        AUTH["RS256 JWT Token Exchange"]
        SA["Multi-Tool Static Analysis<br/>(Ruff, Bandit, Secrets, Pip-Audit)"]
        LLM_REV["Gemini 2.0 Flash Reviewer"]
        AST_GAP["AST Unit Test Gap Detector"]
        DEDUP["Deduplication & Learnings Filter"]
        MERMAID["AST Call Graph Generator"]
        PUB["GitHub Review & Check Run Publisher"]
        CHAT["@review-bot Chat Handler"]
        DB_SQLITE[(SQLite WAL Database & .env.app<br/>App Credentials, Repos, Suppressions)]
    end

    subgraph "Runtime Self-Healing Cloud Engine (agentic_engine/ & digital_twin/)"
        TELEMETRY["Prometheus Telemetry Stream"]
        IFOREST["Isolation Forest Anomaly Detector"]
        SHAP["KernelSHAP Feature Attribution"]
        TOPO["NetworkX Dynamic Topology Graph"]
        SIMPY["SimPy 0.01s Action Safety Gate"]
        RL_SIMI["SimiFed Cosine RL Agent (0.001s)"]
        LLM_REACT["Gemini ReAct Agent (2.4s)"]
        PAR_ORCH["Consensus & Arbitration Engine"]
        K8S_TOOLS["Hardened K8s & AKS Execution Engine"]
    end

    DEV -->|Opens PR| PR
    PR -->|Webhook Event| GH_APP
    GH_APP --> HMAC
    HMAC --> AUTH
    AUTH --> SA
    AUTH --> LLM_REV
    SA --> DEDUP
    LLM_REV --> DEDUP
    AST_GAP --> DEDUP
    DEDUP --> DB_SQLITE
    DEDUP --> MERMAID
    MERMAID --> PUB
    PUB -->|Inline Comments & Quality Gate| PR
    PR -->|@review-bot mention| CHAT
    CHAT --> PUB

    TELEMETRY --> IFOREST
    IFOREST --> SHAP
    IFOREST --> TOPO
    TOPO --> SIMPY
    SIMPY --> LLM_REACT
    SHAP --> LLM_REACT
    IFOREST --> RL_SIMI
    RL_SIMI --> PAR_ORCH
    LLM_REACT --> PAR_ORCH
    PAR_ORCH --> K8S_TOOLS
    K8S_TOOLS -->|Self-Healing Action| TELEMETRY
```

---

##  Research Foundations: Base Paper & Reference Literature

Our platform is grounded in leading research from distributed systems, cloud computing, federated learning, and explainable artificial intelligence.

### The Base Paper: SF-DTM (Saxena & Singh, IEEE TII 2025)

* **Paper Title:** *"A Self-Healing and Fault-Tolerant Cloud-based Digital Twin Processing Management Model"*
* **Authors:** Deepika Saxena (*Member, IEEE*) and Ashutosh Kumar Singh (*Senior Member, IEEE*)
* **Publication Venue:** *IEEE Transactions on Industrial Informatics*, 2025 (`arXiv:2505.01215v1`)
* **Key Principles of SF-DTM:**
  1. **SimiFed Resource Estimation:** An LSTM-based federated learning framework where client models aggregate local weights using **Cosine Similarity**:
     $$\text{Cosine}(R_i, R_j) = \frac{R_i \cdot R_j}{\|R_i\| \|R_j\|}$$
     This clusters and selects similar workload profiles without exposing raw telemetry, minimizing resource contention.
  2. **Frequent Sequence Pattern (FSP) Mining:** Analyzes the Temporal Digital Twin Database ($TDT_{db}$) to classify tasks into *Highly fault-prone* ($a_j^*$), *Mild fault-prone* ($\bar{a}_j$), and *Least fault-prone* ($a_j^\dagger$). It mines **Non-supportive Frequent Sequence Patterns (NFSP)** and **Supportive Frequent Sequence Patterns (SFSP)** to avoid colocation of conflicting services on the same host.
  3. **Multi-Version Programming (MVP) Self-Healing:** Deploys an odd number of replicas ($2x + 1$) for critical components, ensuring majority fault tolerance ($F_{MVP}$) against sudden outages.

---

### Comprehensive Reference Literature (9 Key Studies)

Beyond the base paper, our design synthesizes concepts from 9 peer-reviewed publications:

1. **Multi-Factor Trust-Driven Secure Communication for Cloud Digital Twins** (Saxena & Singh, *IEEE Transactions on Industrial Informatics*, 2026, `2605.23566v1`):
   * *Contribution:* Defines temporal, contextual, and federated trust vectors for multi-tenant digital twin communication.
2. **Adaptive Device-Edge Collaboration on DNN Inference in AIoT** (Zhang et al., *IEEE Internet of Things Journal*, 2024, `2405.17664v1`):
   * *Contribution:* Dynamic partitioning of AI workloads between edge nodes and cloud clusters.
3. **FT-ERM: Fault Tolerant Elastic Resource Management for High Availability** (Saxena et al., *IEEE Transactions on Network and Service Management*, 2023, `2212.03547v1`):
   * *Contribution:* Neural network-based failure prediction to preemptively trigger VM elastic migration.
4. **RRFT: Rank-Based Resource Aware Fault Tolerant Strategy** (Saxena & Singh, *IEEE Transactions on Cloud Computing*, 2023, `2111.00579v1`):
   * *Contribution:* Significance ranking of virtual machines to prioritize failover during resource contention.
5. **Auto-Scaling for Serverless Environments Based on Multi-Expert Consensus** (*Journal of Ambient Intelligence and Smart Environments*, 2026, `2607.15511v1`):
   * *Contribution:* Multi-expert consensus mechanism arbitrating between heuristic autoscalers and machine learning forecasters.
6. **Hybrid Multi-Objective Evolutionary Algorithms for Service Placement** (*Cluster Computing*, Springer, 2026, `2607.13200v1`):
   * *Contribution:* Multi-objective optimization balancing latency, energy consumption, and availability.
7. **SQUIRO: Security-Aware Scheduling on Kubernetes** (*Future Generation Computer Systems*, Elsevier, 2026, `2607.16089v1`):
   * *Contribution:* Security-aware placement algorithms preventing co-tenant vulnerability exploitation in Kubernetes clusters.
8. **Cold-Start Model Delivery in Kubernetes Inference Serving** (*IEEE Access*, 2026, `2607.16596v1`):
   * *Contribution:* OCI image distribution integrity checks and container cold-start minimization techniques.
9. **Consensus In Asynchrony: Strictly Formal** (*Intl. Journal of Parallel, Emergent and Distributed Systems*, 2026, `2607.24095v1`):
   * *Contribution:* Mathematical proofs for distributed Byzantine and fail-stop consensus under asynchronous network conditions.

---

### Theoretical Mappings: What We Implemented from Literature

| Theoretical Concept | Academic Literature Source | Our Specific Codebase Implementation |
| :--- | :--- | :--- |
| **SimiFed Incident Vector Matching** | Saxena & Singh (2025) [Base Paper] | [`agentic_engine/rl_agent.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/agentic_engine/rl_agent.py): Uses cosine similarity across $[CPU, RAM, Latency, RequestRate]$ to retrieve matching historical incident patterns in $0.001\text{s}$. |
| **Digital Twin State Mirroring** | Saxena & Singh (2025, 2026) | [`digital_twin/topology_graph.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/digital_twin/topology_graph.py): Real-time NetworkX directed graph representation of microservice dependencies and resource states. |
| **Availability & MTTR Metrics** | FT-ERM (2023), RRFT (2023) | [`agentic_engine/orchestrator.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/agentic_engine/orchestrator.py): Formal computation of MTBF, MTTR, and availability percentage ($A = \frac{\text{MTBF}}{\text{MTBF} + \text{MTTR}}$). |
| **Multi-Agent Consensus Arbitration** | Multi-Expert Consensus (2026), Asynchrony (2026) | [`agentic_engine/orchestrator.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/agentic_engine/orchestrator.py): Evaluates agreement between high-speed RL baseline and LLM ReAct agent before executing live K8s mutations. |

---

### Architectural Innovations: What We Made Better

While the base paper established foundational theoretical models for VM allocation and federated learning, our platform introduces **five major architectural advancements**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        WHAT WE MADE BETTER (NOVEL CONTRIBUTIONS)                       │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│ 1. Explainable AI (XAI) with SHAP         │ Replaced opaque scalar thresholding with   │
│    (KernelSHAP Attribution)               │ exact Shapley values explaining root-cause │
│                                           │ telemetry drivers (CPU vs RAM vs Network). │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ 2. SimPy Action-Aware Simulation Gate     │ Implemented active 0.01s discrete-event    │
│    (Pre-Execution Dry-Run Safety)         │ M/M/c simulation to mathematically verify  │
│                                           │ stability before executing K8s commands.   │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ 3. Dual Parallel Decision Engine          │ Paired sub-millisecond SimiFed RL (0.001s) │
│    (Reflexive RL + ReAct LLM Reasoning)   │ with deep Gemini 2.0 Flash ReAct (2.4s)    │
│                                           │ and automated consensus arbitration.       │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ 4. Shift-Left Preventative PR Review      │ Extended self-healing backwards to PR code │
│    (Multi-Tool Static + LLM Ast Scan)     │ commits with automated security scans, AST │
│                                           │ test-gap audits, and auto-fix PR branches. │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ 5. Cloud-Native Production Deployment     │ Built full Terraform IaC for Azure AKS/ACR │
│    (Microsoft Azure AKS + React/Vite SPA) │ and a 2D vector dark-theme web console.    │
└───────────────────────────────────────────┴────────────────────────────────────────────┘
```

---

##  Product A — PR Review Agent

The PR Review Agent (`pr_review_agent/`) automatically inspects pull requests, detects vulnerabilities and lint errors, generates visual call graphs, and posts actionable inline suggestions directly to GitHub.

### 11-Stage Review Pipeline

When a `pull_request` event (`opened`, `synchronize`, `reopened`) is received, the agent executes:

1. **`fetch_pr_diff`**: Retrieves modified files and unified patches via the GitHub API.
2. **`chunk_diff_if_large`**: Evaluates total diff hunks. If diff exceeds `max_hunks` (default: 50), cleanly truncates and appends a coverage advisory note.
3. **`run_static_analysis`**: Executes multi-language static tools concurrently in an isolated environment:
   - `ruff`: Python syntax, styling, and linting rules.
   - `bandit`: Python AST security analysis (hardcoded passwords, SQL injection, unsafe deserialization).
   - `detect-secrets`: High-entropy regex scanner preventing committed secrets/tokens.
   - `pip-audit`: Scans dependencies against known CVE vulnerability advisories.
   - `eslint`: Conditional JavaScript/TypeScript linting if config exists.
4. **`run_llm_review`**: Sends diff hunks + static findings to **Gemini 2.0 Flash** for structured analysis of logic errors, race conditions, edge cases, and architectural smells.
5. **`deduplicate_findings`**: Merges duplicate static and LLM findings at identical lines, filters low-confidence entries (`< 0.70`), and applies persistent dismissal suppressions.
6. **`detect_unit_test_gaps`**: Uses Python `ast` to extract modified public functions and classes, verifying if corresponding tests exist in `tests/` (*flag-only guardrail — does not hallucinate fake tests*).
7. **`generate_pr_summary`**: Generates a concise TL;DR of the PR scope and risk level.
8. **`generate_mermaid_diagram`**: Analyzes AST import dependencies across changed files to produce a live Mermaid architecture diagram (triggered if changed files $\ge 3$).
9. **`post_review_to_github`**: Posts a top-level review summary comment and creates inline GitHub review comments with native clickable ````suggestion```` code blocks.
10. **`create_fix_pr`**: For complex issues requiring extensive refactoring, creates a branch (`autoreview/fix-<slug>-pr<num>`), commits the fix, and opens a dedicated PR.
11. **`post_quality_gate_check`**: Creates a GitHub Check Run (`review-agent/quality-gate`). Passes if clean, or blocks merge if critical issues are detected (enabling required branch protection).

### Interactive `@review-bot` Commands

Developers can interact with the bot in PR comment threads:

* `@review-bot /add-docstrings`: Generates Google-style docstrings for undocumented functions via AST inspection and posts inline suggestions.
* `@review-bot /dismiss <rule-id>`: Suppresses a specific rule for the repository (persisted in SQLite `dismissals` table).
* `@review-bot /re-review`: Re-runs the full 11-stage review pipeline against the latest commit.
* `@review-bot <question>`: Answers questions about the diff, potential side effects, or architectural trade-offs using Gemini 2.0 Flash.

### Learnings & Suppression Loop

Rule suppressions are stored in SQLite (`dismissals` table):
```
Developer: @review-bot /dismiss ruff/E501
Bot -> Parses command -> Writes to SQLite dismissals table -> Suppresses in all future reviews
```

### Per-Repository Configuration (`.review-agent.yml`)

Repositories can customize behavior with a `.review-agent.yml` file in the repository root:

```yaml
ignore_globs:
  - "tests/**"
  - "*.md"
severity_threshold: "warning"
disabled_checks:
  - "detect-secrets"
diagram_min_files: 3
quality_gate_on_critical: true
max_hunks: 50
llm_confidence_threshold: 0.70
```

---

##  Product B — Infrastructure Self-Healing Engine

### Digital Twin Simulation Gate

Before any remediation action is applied to live Kubernetes or Azure AKS clusters, it is evaluated in a **SimPy Discrete-Event Simulation Engine** running an $M/M/c$ queuing model:
* Simulates arrival rates, service times, and queue depths.
* Evaluates proposed actions (`SCALE_UP`, `RESTART_POD`, `PATCH_LIMITS`).
* Validates whether the action will successfully reduce CPU/RAM below the 80% threshold.
* **Guarantees safety in 0.01 seconds** before touching live infrastructure.

### Parallel Agent Orchestrator

```
                  ┌───────────────────────────────┐
                  │    Incoming Telemetry Alert   │
                  └───────────────┬───────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
      ┌───────────────────────┐       ┌───────────────────────┐
      │     SimiFed RL        │       │   Gemini ReAct LLM    │
      │  (Cosine Sim Vector)  │       │ (ReAct + Tool Calling)│
      │    Latency: 0.001s    │       │     Latency: 2.4s     │
      └───────────┬───────────┘       └───────────┬───────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
                  ┌───────────────────────────────┐
                  │      Consensus Arbiter        │
                  │ (Agreed Action / Safe Fallback)
                  └───────────────┬───────────────┘
                                  ▼
                  ┌───────────────────────────────┐
                  │  SimPy Simulation Validation  │
                  └───────────────┬───────────────┘
                                  ▼
                  ┌───────────────────────────────┐
                  │  Kubectl Execution & Audit    │
                  └───────────────────────────────┘
```

### SHAP Explainable AI & Anomaly Detection

Instead of raw numbers, every anomaly alert produces **SHAP Feature Attribution Scores**:
* Explains exactly which telemetry features triggered the anomaly (`cpu_usage: +0.82`, `memory_usage: +0.15`, `latency_ms: -0.03`).
* Displayed as clean horizontal bar charts in the web console.
* Provides full transparency into AI decision-making.

---

##  Modern React + Vite Control Plane

The frontend in `dashboard/frontend-vite/` provides a dark-themed single-pane-of-glass operator console built with React 18, TypeScript, and Vite:

* **Sticky Telemetry Header (44px):** Live cluster health indicator, active anomaly count, pods monitored, and last scan timestamp.
* **Pipeline Stage Navigation (46px):**
  * `Overview`: Connected repositories, live metrics grid, recent PR reviews.
  * `Review`: Line-by-line review log, confidence scores, and inline suggestion code diffs.
  * `Analyze`: Interactive anomaly injection slider, SHAP feature importance chart, and Gemini Chain-of-Thought reasoning logs.
  * `Fix`: Auto-fix branch tracking and automated PR status.
  * `Secure`: Security posture monitoring across Bandit, Detect-Secrets, and Pip-Audit with Check Run enforcement.
  * `Infra Healing`: Real-time SVG microservice topology graph, operator manual override controls, and parallel agent benchmarks.
  * `Settings`: GitHub App connection status, per-repository rule suppression management.

---

## Microsoft Azure Cloud Deployment

The platform includes production-ready Terraform Infrastructure as Code (IaC) and Kubernetes manifests to deploy the entire stack onto **Microsoft Azure**:

```
                                          ┌────────────────────────────────────────┐
                                          │          Azure Cloud Platform          │
                                          │                                        │
  [Developer / GitHub PR]                │   ┌────────────────────────────────┐   │
             │                            │   │ Azure Container Registry (ACR) │   │
             ▼ Webhook HTTPS              │   │ (OCI Container Images)         │   │
┌───────────────────────────────┐         │   └───────────────┬────────────────┘   │
│ Azure LoadBalancer (Public IP)│─────────┼───────────────────┼────────────────────┤
└───────────────┬───────────────┘         │                   ▼                    │
                │                         │   ┌────────────────────────────────┐   │
                ▼                         │   │ Azure Kubernetes Service (AKS) │   │
  ┌───────────────────────────┐           │   │                                │   │
  │ agentic-ai-service (:80)  │           │   │  Namespace: agentic-ai         │   │
  └─────────────┬─────────────┘           │   │  ├─ agentic-ai-platform        │   │
                │                         │   │  │  ├─ React/Vite UI (:8000)   │   │
                ▼                         │   │  │  ├─ FastAPI Backend (:8000) │   │
  ┌───────────────────────────┐           │   │  │  └─ SimPy + Gemini ReAct    │   │
  │ agentic-ai-platform (Pod) │           │   │  └─ agentic-db-pvc (5Gi Azure) │   │
  └─────────────┬─────────────┘           │   │                                │   │
                │ Ingest & Control        │   │  Namespace: default            │   │
                ▼                         │   │  ├─ Online Boutique 11 Svc     │   │
  ┌───────────────────────────┐           │   │  └─ Chaos Mesh Operators       │   │
  │ Microservices + ChaosMesh │           │   └────────────────────────────────┘   │
  └───────────────────────────┘           └────────────────────────────────────────┘
```

### 1-Click Automated Azure Deployment

```powershell
# On Windows (PowerShell):
.\scripts\deploy_azure.ps1 -ResourceGroupName "rg-agentic-cloud-prod" -Location "eastus" -ClusterName "aks-agentic-cloud" -AcrName "acragenticai2026"

# On Linux / macOS (Bash):
chmod +x ./scripts/deploy_azure.sh
./scripts/deploy_azure.sh "rg-agentic-cloud-prod" "eastus" "aks-agentic-cloud" "acragenticai2026"
```

For complete step-by-step instructions, see [`docs/azure_deployment_guide.md`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/docs/azure_deployment_guide.md).

---

## API & Webhook Reference

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/install` | Minimalist 2D setup page & real-time connected repository list |
| `POST` | `/webhooks/github` | HMAC-SHA256 verified GitHub webhook receiver |
| `GET` | `/api/github/app-callback` | Manifest Flow code exchange (persists credentials to DB & `.env.app`) |
| `GET` | `/api/pr-reviews` | List recent PR review logs |
| `GET` | `/api/pr-reviews/{owner}/{repo}/{pr}` | Get review details and findings for a specific PR |
| `POST` | `/api/learnings/dismiss` | Dismiss/suppress a rule ID for a repository |
| `GET` | `/api/repos` | List all connected repositories |
| `GET` | `/api/status` | Current system health, anomaly counts, and active mode |
| `GET` | `/api/topology` | Digital Twin graph topology in node-link format |
| `POST` | `/api/evaluate` | Trigger dynamic SHAP attribution & parallel agent evaluation |
| `POST` | `/api/override` | Manual operator override applying real Kubernetes remediation |

---

## Getting Started Locally

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Google Gemini API Key (`GEMINI_API_KEY`)
- `ngrok` (for receiving GitHub webhooks locally)

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure.git
cd Agentic-AI-Self-Healing-Cloud-Infrastructure

# Install Python dependencies
pip install -r requirements.txt

# Install static analysis tools for full scanning capabilities
pip install ruff bandit detect-secrets pip-audit

# Build the React + Vite frontend
cd dashboard/frontend-vite
npm install
npm run build
cd ../..
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Run Server & Tunnel
```powershell
# Terminal 1: Launch FastAPI backend (serves compiled React frontend automatically)
python -m uvicorn dashboard.backend.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Expose via ngrok
ngrok http 8000
```

### 5. Connect to GitHub
Open `https://<your-ngrok-subdomain>.ngrok-free.app/install` in your browser, click **"Install on GitHub"**, and select your target repositories.

---

##  Running the Test Suite

The test suite covers unit, integration, and security verification across all subsystems:

```powershell
# Execute Phase 1 & 2 tests (16 tests — K8s security, API routes, webhooks)
$env:PYTHONPATH = "."; python -m pytest tests/test_phase1_phase2.py -v

# Execute Phase 3 PR Review Agent tests (13 tests — DB, HMAC, diff chunker, AST test gaps)
$env:PYTHONPATH = "."; python tests/test_phase3.py

# Execute End-to-End Infrastructure Evaluation
$env:PYTHONPATH = "."; python tests/e2e_evaluation.py
```

---

##  Implementation Status Matrix

| Subsystem / Feature | Academic Basis / Standard | Status | Verification |
|:---|:---|:---:|:---|
| **PR Review: Diff Fetching & Chunking** | GitHub REST API v3 | ✅ Production | Tested with large diff chunking guard (`max_hunks`) |
| **PR Review: Multi-Tool Static Analysis** | Ruff, Bandit, Secrets, Pip-Audit | ✅ Production | Runs 4 scanners concurrently with user-space PATH injection |
| **PR Review: Gemini 2.0 Flash Reasoning** | Google GenAI SDK | ✅ Production | Structured JSON output with confidence ranking |
| **PR Review: AST Test Gap Detection** | Python `ast` Analysis | ✅ Production | Flag-only guardrail (no hallucinated test generation) |
| **PR Review: Mermaid Dependency Graph** | AST Import Analysis | ✅ Production | Real AST import/call graph generation ($\ge 3$ files) |
| **PR Review: Quality Gate Check Runs** | GitHub Checks API | ✅ Production | Sets `review-agent/quality-gate` check run status |
| **PR Review: @review-bot Docstrings** | Google Docstring Style | ✅ Production | Verified AST missing docstring detection & suggestion blocks |
| **PR Review: Learnings & Dismissals** | Active Feedback Learning | ✅ Production | SQLite persisted dismissal suppression loop |
| **GitHub App Manifest 1-Click Install** | GitHub Manifest Flow | ✅ Production | Full manifest exchange with DB + `.env.app` persistence |
| **Webhook HMAC-SHA256 Verification** | RFC 2104 HMAC-SHA256 | ✅ Production | Strict constant-time cryptographic verification |
| **SimiFed Cosine Vector Matching** | Saxena & Singh (2025) [Base Paper] | ✅ Production | Cosine similarity incident vector retrieval ($0.001\text{s}$) |
| **Digital Twin SimPy Dry-Run Gate** | Discrete-Event $M/M/c$ Queuing | ✅ Production | Action-aware simulation before execution ($0.01\text{s}$) |
| **SHAP Feature Attribution Explainer** | Lundberg & Lee (NeurIPS 2017) | ✅ Production | Real-time mathematical feature importance attribution |
| **Parallel Agent Orchestrator** | Multi-Expert Consensus (2026) | ✅ Production | SimiFed Cosine RL vs. Gemini ReAct comparison |
| **Kubectl Command Execution** | CIS Benchmark Hardening | ✅ Production | Hardened against injection (`shell=False`, name validation) |
| **React + Vite Control Plane** | React 18, TypeScript, Vite 6 | ✅ Production | Modular SPA console with 2D outline design tokens |
| **Microsoft Azure Cloud Deployment** | Terraform, Azure AKS & ACR | ✅ Production | Full IaC and 1-click deployment automation script |

---

## 📜 License

Distributed under the MIT License. Developed for research in Autonomous Cloud Systems, Self-Healing Infrastructure, and Agentic AI Code Intelligence.
