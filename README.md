# Agentic AI — Self-Healing Infrastructure & PR Review Agent

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-2.0%20Flash-4285F4.svg)](https://ai.google.dev/)
[![GitHub App](https://img.shields.io/badge/GitHub%20App-Manifest%20Flow-181717.svg)](https://docs.github.com/en/apps)
[![Tests](https://img.shields.io/badge/Tests-29%20Passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> An autonomous cloud reliability and developer velocity platform combining **Automated Code Review with Quality Gates** and **Predictive Self-Healing Cloud Infrastructure** powered by Digital Twin Simulations, SHAP Explainable AI, and Parallel ReAct LLM Reasoning.

---

##  Table of Contents

- [Executive Overview](#-executive-overview)
- [System Architecture](#-system-architecture)
- [Product A — PR Review Agent (`pr_review_agent/`)](#-product-a--pr-review-agent)
  - [11-Stage Review Pipeline](#11-stage-review-pipeline)
  - [Interactive `@review-bot` Commands](#interactive-review-bot-commands)
  - [Learnings & Suppression Loop](#learnings--suppression-loop)
  - [Per-Repository Configuration (`.review-agent.yml`)](#per-repository-configuration-review-agentyml)
- [Product B — Infrastructure Self-Healing Engine (`agentic_engine/`)](#-product-b--infrastructure-self-healing-engine)
  - [Digital Twin Simulation Gate (`digital_twin/`)](#digital-twin-simulation-gate)
  - [Parallel Agent Orchestrator (RL Baseline vs. Gemini ReAct)](#parallel-agent-orchestrator)
  - [SHAP Explainable AI & Anomaly Detection](#shap-explainable-ai--anomaly-detection)
- [GitHub App 1-Click Manifest Flow](#-github-app-1-click-manifest-flow)
- [Repository Structure](#-repository-structure)
- [API & Webhook Reference](#-api--webhook-reference)
- [Getting Started Locally](#-getting-started-locally)
- [Running the Test Suite](#-running-the-test-suite)
- [Implementation Status Matrix](#-implementation-status-matrix)
- [License](#-license)

---

##  Executive Overview

Modern cloud engineering teams face two critical operational bottlenecks:
1. **PR Review Velocity & Security Drift:** Code reviews take hours or days; subtle security vulnerabilities, dependency CVEs, missing unit tests, and secret leaks slip into main branches.
2. **Reactive Cloud Outages:** Traditional autoscaling (HPA / Cloud Run) waits 3–5 minutes after CPU breaches thresholds, applies blunt scaling without considering business logic, and risks cascading failures during pod restarts.

This repository provides an integrated, dual-engine solution:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AGENTIC AI PLATFORM                           │
├────────────────────────────────────┬────────────────────────────────────┤
│   PRODUCT A: PR REVIEW AGENT       │   PRODUCT B: SELF-HEALING INFRA    │
│  • Static Analysis + Gemini LLM    │  • Isolation Forest + XGBoost IDS  │
│  • AST Test Gap Detection          │  • PyTorch LSTM Resource Predictor │
│  • Inline Suggestions & Fix PRs    │  • SimPy Digital Twin Safety Gate  │
│  • Quality Gate Check Runs         │  • SimiFed RL vs. Gemini ReAct     │
│  • Interactive @review-bot Chat    │  • Kubernetes Execution & GitOps   │
└────────────────────────────────────┴────────────────────────────────────┘
```

---

##  System Architecture

```mermaid
graph TB
    subgraph "GitHub Ecosystem"
        DEV["Developer / Team"]
        PR["Pull Request / Issue"]
        GH_APP["GitHub App & Webhooks"]
    end

    subgraph "Product A — PR Review Engine (pr_review_agent/)"
        HMAC["HMAC-SHA256 Verifier"]
        AUTH["JWT / App Auth Token Cache"]
        SA["Static Analysis Engine<br/>(Ruff, Bandit, Secrets, Pip-Audit)"]
        LLM_REV["Gemini 2.0 Flash Reviewer"]
        AST_GAP["AST Test Gap Detector"]
        DEDUP["Deduplication & Learnings Filter"]
        MERMAID["AST Call Graph Generator"]
        PUB["GitHub Review & Check Run Publisher"]
        CHAT["@review-bot Chat & Docstrings Engine"]
        DB_SQLITE[(SQLite DB & .env.app<br/>Credentials, Repos, Dismissals)]
    end

    subgraph "Product B — Self-Healing Infra (agentic_engine/ & digital_twin/)"
        TELEMETRY["Metrics & Log Stream"]
        IFOREST["Isolation Forest + SHAP Explainer"]
        TOPO["NetworkX Topology Graph"]
        SIMPY["SimPy Discrete Event Simulator"]
        RL_SIMI["SimiFed Cosine RL Baseline"]
        LLM_REACT["Gemini ReAct Agent"]
        PAR_ORCH["Parallel Orchestrator"]
        K8S_TOOLS["K8s Execution Tools (Restart, Scale, Patch)"]
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
    IFOREST --> TOPO
    TOPO --> SIMPY
    SIMPY --> LLM_REACT
    IFOREST --> LLM_REACT
    IFOREST --> RL_SIMI
    RL_SIMI --> PAR_ORCH
    LLM_REACT --> PAR_ORCH
    PAR_ORCH --> K8S_TOOLS
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
   - `pip-audit`: Scans `requirements.txt` against known CVE vulnerability advisories.
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

| Command | Action Performed |
|:---|:---|
| `@review-bot generate docstrings` | Scans changed Python files with `ast` to find functions **actually missing docstrings**, generates Google-style docstrings with Gemini, and posts suggestion diffs. |
| `@review-bot dismiss <rule_id>` | Permanently suppresses the specified rule (e.g. `ruff/E501`) for this repository. |
| `@review-bot re-review` | Re-triggers the full 11-stage analysis pipeline immediately. |
| `@review-bot <any question>` | Answers questions with full context of the PR diff and prior comment history. |

### Learnings & Suppression Loop

When a rule is dismissed via `@review-bot dismiss <rule>` or the dashboard UI, it is persisted to the `dismissals` table in SQLite (`pr_review_agent/db.py`). Subsequent reviews on that repository automatically filter out matching findings, preventing repetitive developer friction.

### Per-Repository Configuration (`.review-agent.yml`)

Place a `.review-agent.yml` in the root of any repository to customize behavior:

```yaml
# .review-agent.yml
severity_threshold: "warning"       # info | warning | error | critical
quality_gate_on_critical: true      # Block PR merge on critical findings
max_hunks: 50                       # Maximum hunks before diff truncation
diagram_min_files: 3                # Min files needed to render Mermaid graph
disabled_checks:
  - "ruff/E501"                     # Disable specific rule or tool
ignore_globs:
  - "docs/**"
  - "*.md"
```

---

##  Product B — Infrastructure Self-Healing Engine

The infrastructure self-healing engine (`agentic_engine/` + `digital_twin/`) monitors running clusters and microservices, analyzes telemetry anomalies, and applies safe remediation actions.

### Digital Twin Simulation Gate

Before any Kubernetes remediation action (`restart_pod`, `scale_deployment`, `patch_resource_limits`) is executed, it passes through the **SimPy Discrete-Event Simulation Gate**:
- Simulates the cluster state 0.01 seconds into the future under current request load.
- Evaluates whether restarting a pod will drop active user sessions or cause cascading memory pressure on downstream nodes.
- Marks action as `SAFE_TO_EXECUTE` or `UNSAFE` with predicted post-remediation metrics.

### Parallel Agent Orchestrator

The orchestrator runs two distinct decision engines concurrently for real-time comparison:
1. **SimiFed RL Agent (`rl_agent.py`)**: Fast Q-Learning baseline using cosine similarity across historical incident embeddings ($< 5\text{ms}$ latency).
2. **Gemini ReAct Agent (`llm_agent.py`)**: Multi-step Chain-of-Thought agent executing *Reason $\rightarrow$ Simulate $\rightarrow$ Act* loops with root-cause explanations.

### SHAP Explainable AI & Anomaly Detection

- **Anomaly Detection**: `MetricsAnomalyDetector` uses an Isolation Forest trained on CPU, memory, request rates, and latency.
- **SHAP Attribution**: `SHAPExplainer` calculates exact marginal feature contributions (e.g. `{"cpu_usage": +0.82, "memory_usage": +0.15}`), providing mathematical ground truth to the LLM agent.

---

##  GitHub App 1-Click Manifest Flow

The platform uses GitHub's **App Manifest Flow** for zero-friction installation:
- **Zero Token Sharing**: Developers never share Personal Access Tokens (PATs).
- **1-Click Registration**: Visiting `/install` generates a pre-configured manifest and submits it to GitHub.
- **Durable Credential Persistence**: The callback endpoint (`/api/github/app-callback`) receives the App ID, webhook secret, and RSA private key, persisting them to **both**:
  1. The SQLite database (`data/pr_review_agent.db`)
  2. The local `.env.app` file (protected by `.gitignore`)
- **JWT & Token Exchange**: Generates RS256 JWTs and exchanges them for short-lived (1-hour) installation tokens, cached in-memory with automatic refresh buffers.

---

##  Repository Structure

```
├── agentic_engine/                  # Product B: Self-Healing Infrastructure
│   ├── orchestrator.py              # Parallel Agent Orchestrator (RL + LLM)
│   ├── rl_agent.py                  # SimiFed Cosine-Similarity Q-Learning Agent
│   ├── llm_agent.py                 # Gemini ReAct Reasoning Loop
│   └── tools/
│       ├── k8s_tools.py             # Kubectl command execution (Restart, Scale, Patch)
│       ├── github_tools.py          # GitOps PR generation & webhook helper
│       └── simpy_tools.py           # SimPy dry-run digital twin tool
├── digital_twin/                    # Digital Twin & Predictive Models
│   ├── topology_graph.py            # NetworkX microservice graph representation
│   ├── simpy_engine.py              # SimPy discrete-event cluster simulation
│   ├── predictive_forecaster.py     # PyTorch LSTM time-series resource forecaster
│   └── state_synchronizer.py        # Telemetry state synchronization
├── detection/                       # Anomaly Detection & Explainability
│   ├── anomaly/isolation_forest.py  # Isolation Forest metrics anomaly detector
│   ├── intrusion/xgboost_ids.py     # XGBoost network intrusion classifier
│   └── explainer/shap_explainer.py  # SHAP feature attribution explainer
├── pr_review_agent/                 # Product A: PR Review Agent Subsystem
│   ├── __init__.py                  # SQLite initialization & .env.app bootstrapper
│   ├── db.py                        # SQLite schema & persistence layer (5 tables)
│   ├── github_app_auth.py           # RS256 JWT generation & installation token exchange
│   ├── config.py                    # .review-agent.yml parser & ReviewConfig dataclass
│   ├── pipeline.py                  # 11-stage review pipeline & orchestrator
│   ├── learnings.py                 # Rule dismissal CRUD & suppression filter
│   ├── chat_handler.py              # @review-bot command router (docstrings, Q&A)
│   └── webhook_handler.py           # FastAPI router, HMAC verifier, /install UI
├── dashboard/                       # Operator Dashboard & Backend API
│   ├── backend/main.py              # FastAPI server mounting all agents & routes
│   └── frontend/index.html          # High-density dark UI (SVG graphs & XAI charts)
├── tests/                           # Complete Test Suite (29 tests)
│   ├── test_phase1_phase2.py        # Bug fixes, k8s security, webhook tests (16 tests)
│   ├── test_phase3.py               # PR Review agent, DB, config, HMAC tests (13 tests)
│   └── e2e_evaluation.py            # End-to-end self-healing evaluation
├── github-app-manifest.json         # GitHub App 1-Click Manifest definition
├── requirements.txt                 # Project dependencies
└── README.md
```

---

##  API & Webhook Reference

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/install` | Minimalist 2D setup page & connected repository status |
| `POST` | `/webhooks/github` | HMAC-SHA256 verified GitHub webhook receiver |
| `GET` | `/api/github/app-callback` | Manifest Flow code exchange (persists credentials) |
| `GET` | `/api/pr-reviews` | List recent PR review logs |
| `GET` | `/api/pr-reviews/{owner}/{repo}/{pr}` | Get review details for a specific PR |
| `POST` | `/api/learnings/dismiss` | Dismiss a rule ID for a repository |
| `GET` | `/api/repos` | List all connected repositories |
| `GET` | `/api/status` | Current system health, anomaly counts, and active mode |
| `GET` | `/api/topology` | Digital Twin graph topology in node-link format |
| `POST` | `/api/evaluate` | Trigger dynamic SHAP attribution & parallel evaluation |
| `POST` | `/api/override` | Manual operator override applying real remediation |

---

##  Getting Started Locally

### 1. Prerequisites
- Python 3.10+
- Google Gemini API Key (`GEMINI_API_KEY`)
- `ngrok` (for receiving GitHub webhooks locally)

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure.git
cd Agentic-AI-Self-Healing-Cloud-Infrastructure

# Install dependencies
pip install -r requirements.txt

# (Optional) Install static analysis tools for complete local scanning
pip install ruff bandit detect-secrets pip-audit
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Run Server & Tunnel
```powershell
# Terminal 1: Launch FastAPI backend
python -m uvicorn dashboard.backend.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Expose via ngrok
ngrok http 8000
```

### 5. Connect to GitHub
Open `https://<your-ngrok-subdomain>.ngrok-free.app/install` in your browser, click **"Install on GitHub"**, and select your target repositories!

---

##  Running the Test Suite

The test suite covers unit, integration, and security verification across all subsystems:

```powershell
# Set PYTHONPATH and execute Phase 1 & 2 tests (16 tests)
$env:PYTHONPATH = "."; python tests/test_phase1_phase2.py

# Execute Phase 3 PR Review Agent tests (13 tests)
$env:PYTHONPATH = "."; python tests/test_phase3.py

# Execute End-to-End Infrastructure Evaluation
$env:PYTHONPATH = "."; python tests/e2e_evaluation.py
```

---

##  Implementation Status Matrix

| Subsystem / Feature | Status | Notes |
|:---|:---:|:---|
| **PR Review: Diff Fetching & Chunking** | ✅ Implemented | Tested with large diff chunking guard (`max_hunks`) |
| **PR Review: Multi-Tool Static Analysis** | ✅ Implemented | Ruff, Bandit, Detect-Secrets, Pip-Audit, ESLint |
| **PR Review: Gemini 2.0 Flash Reasoning** | ✅ Implemented | Structured JSON output with confidence ranking |
| **PR Review: AST Test Gap Detection** | ✅ Implemented | Flag-only guardrail (no hallucinated test generation) |
| **PR Review: Mermaid Dependency Graph** | ✅ Implemented | Real AST import/call graph generation |
| **PR Review: Quality Gate Check Runs** | ✅ Implemented | Sets `review-agent/quality-gate` check run status |
| **PR Review: @review-bot Docstrings** | ✅ Implemented | Verified AST missing docstring detection & suggestion blocks |
| **PR Review: Learnings & Dismissals** | ✅ Implemented | SQLite persisted dismissal suppression loop |
| **GitHub App Manifest 1-Click Install** | ✅ Implemented | Full manifest exchange with DB + `.env.app` persistence |
| **Webhook HMAC-SHA256 Verification** | ✅ Implemented | Strict constant-time cryptographic verification |
| **Digital Twin SimPy Dry-Run Gate** | ✅ Implemented | Action-aware discrete event simulation before execution |
| **SHAP Feature Attribution Explainer** | ✅ Implemented | Real-time mathematical feature importance attribution |
| **Parallel Agent Orchestrator** | ✅ Implemented | SimiFed Cosine RL vs. Gemini ReAct agent comparison |
| **Kubectl Command Execution** | ✅ Implemented | Hardened against injection (`shell=False`, name validation) |
| **Vite Dashboard Migration** | 🚧 Planned (Phase 5) | Static HTML/SVG dashboard active; React/Vite port queued |

---

##  License

Distributed under the MIT License. Developed for research in Autonomous Cloud Systems and Agentic AI Code Intelligence.
