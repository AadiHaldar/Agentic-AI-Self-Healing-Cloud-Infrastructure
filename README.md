# Agentic AI Self-Healing Cloud Infrastructure — Implementation Plan

> A unified, scalable implementation merging the **SF-DTM** model (federated resource estimation + fault-tolerant allocation) with the **Agentic AI + Digital Twin + Explainable AI** three-layer architecture into a single deployable system.

---

## 1. High-Level Architecture Overview

The system is decomposed into **five major subsystems**:

```mermaid
graph TB
    subgraph "Live Cloud Infrastructure (Local / Azure AKS)"
        K8S["Kubernetes Cluster<br/>(Multi-node)"]
        APPS["Microservice Application<br/>(Online Boutique)"]
        CHAOS["Chaos Mesh<br/>(Fault Injection)"]
    end

    subgraph "Layer 1 — Telemetry & Monitoring"
        PROM["Prometheus"]
        GRAF["Grafana"]
        LOKI["Loki (Logs)"]
        KAFKA["Kafka / Redis Streams<br/>(Event Bus)"]
    end

    subgraph "Layer 2 — Digital Twin Engine"
        TWIN_SYNC["State Synchronizer"]
        TWIN_MODEL["SimPy Simulation Engine"]
        TWIN_PRED["Predictive Forecaster<br/>(LSTM / Prophet)"]
        TWIN_FED["SimiFed Module<br/>(Federated Learning)"]
    end

    subgraph "Layer 3 — Anomaly & Intrusion Detection"
        AD_MODEL["Anomaly Detection<br/>(Isolation Forest)"]
        IDS["Intrusion Detection<br/>(XGBoost)"]
        XAI_DET["Detection Explainer<br/>(SHAP)"]
    end

    subgraph "Layer 4 — Agentic AI Decision Engine"
        RL_AGENT["RL Policy Agent<br/>(PPO)"]
        LLM_AGENT["LLM Tool-Calling Agent<br/>(Ollama / Gemini)"]
        ACTION_SPACE["Action Space Manager"]
        SF_ALLOC["Self-Healing Allocator<br/>(Fault-Pattern Mining)"]
        XAI_ACT["Action Explainer<br/>(Structured Rationale)"]
    end

    subgraph "Layer 5 — Operator Interface & Audit"
        DASH["Operator Dashboard<br/>(React + WebSocket)"]
        AUDIT["Audit Log Store<br/>(PostgreSQL)"]
    end

    K8S --> PROM
    APPS --> PROM
    PROM --> KAFKA
    LOKI --> KAFKA
    KAFKA --> TWIN_SYNC
    KAFKA --> AD_MODEL
    TWIN_SYNC --> TWIN_MODEL
    TWIN_MODEL --> TWIN_PRED
    TWIN_FED --> TWIN_PRED
    AD_MODEL --> XAI_DET
    IDS --> XAI_DET
    TWIN_PRED --> RL_AGENT
    TWIN_PRED --> LLM_AGENT
    XAI_DET --> RL_AGENT
    XAI_DET --> LLM_AGENT
    RL_AGENT --> ACTION_SPACE
    LLM_AGENT --> ACTION_SPACE
    ACTION_SPACE --> SF_ALLOC
    ACTION_SPACE --> XAI_ACT
    XAI_ACT --> AUDIT
    SF_ALLOC --> K8S
    ACTION_SPACE --> K8S
    CHAOS --> K8S
    AUDIT --> DASH
    PROM --> GRAF
    XAI_ACT --> DASH
```

---

## 2. Technology Stack

| Component | Technology | Justification |
|---|---|---|
| **Container Orchestration** | Kubernetes (k3s for Local, Azure AKS for Cloud) | Easy local testing with path to Azure production. |
| **Microservice App** | Google Online Boutique | Realistic microservice topology to test faults on. |
| **Metrics & Logs** | Prometheus + Grafana + Loki | De facto cloud-native monitoring standard. |
| **Event Bus** | Redis Streams / Kafka | Decouples telemetry producers from twin/detection consumers. |
| **Digital Twin Simulation** | Python + SimPy | Fast discrete-event simulation to model K8s resources. |
| **Federated Learning** | Flower (flwr) framework | Handles the SimiFed collaborative forecasting model. |
| **Anomaly & IDS** | scikit-learn (Isolation Forest) + XGBoost | Fast and robust models for telemetry and network flows. |
| **Explainability (XAI)**| SHAP | Feature attribution to explain why an anomaly was triggered. |
| **RL Agent** | Stable-Baselines3 (PPO) + Gymnasium | Learns long-term remediation policies in the twin environment. |
| **LLM Agent** | LangChain + Ollama (Local) / Gemini | Acts as an alternative/advisory decision maker with structured reasoning. |
| **Fault Injection** | Chaos Mesh | K8s-native chaos engineering to simulate pod crashes, CPU hogs, network delays. |
| **Dashboard** | React + Vite + WebSocket | Real-time observability for the operator to approve/audit decisions. |
| **Audit DB** | PostgreSQL | Relational storage for decisions, confidence scores, and rationales. |

---

## 3. Implementation Phases (8-Week MVP)

This timeline compresses the work into an 8-week maximum schedule by focusing on MVP implementations of each layer.

### Phase 1: Foundation & Infrastructure (Weeks 1-2)
- **Local K8s Setup:** Deploy a local Kubernetes cluster (k3s / minikube).
- **Azure Preparation:** Prepare Terraform/scripts for Azure AKS deployment (for later).
- **Application Deploy:** Install Google Online Boutique microservices.
- **Monitoring Stack:** Deploy Prometheus, Loki, and Grafana.
- **Chaos Mesh:** Install Chaos Mesh to verify we can artificially kill pods or throttle CPU.

### Phase 2: Digital Twin & Detection MVP (Weeks 3-4)
- **Telemetry Pipeline:** Stream metrics from Prometheus into Python.
- **SimPy Digital Twin:** Build a basic node-pod graph in SimPy to model current state.
- **Predictive Forecaster:** Train a lightweight LSTM to predict resource exhaustion 5-10 mins ahead.
- **Detection Models:** Train Isolation Forest (for metrics anomalies) and a basic XGBoost IDS (for security).
- **Explainability:** Wrap models with SHAP to generate feature importance arrays.

### Phase 3: Agentic Decision Engine (Weeks 5-6)
- **RL Agent:** Create a Gymnasium environment wrapping the Twin. Train a PPO agent on basic fault scenarios (e.g., if CPU > 90%, action = SCALE_OUT).
- **LLM Agent:** Build a LangChain tool-caller using a local model (via Ollama) or Gemini. Feed it SHAP scores and Twin predictions, asking for a structured JSON decision.
- **Agent Parallelization:** Run both RL and LLM agents. Store both of their recommendations.
- **Self-Healing Allocator:** Implement the fault-pattern mining logic to decide *where* to place migrated workloads.

### Phase 4: Operator Dashboard & Cloud Deployment (Weeks 7-8)
- **Backend API:** FastAPI server to expose decisions and twin state.
- **React Dashboard:** Simple UI showing live topology, active alerts, and side-by-side agent decisions (RL vs LLM) with their explanations.
- **Cloud Migration:** Deploy the entire stack to Azure AKS using Azure Free Credits.
- **Final Evaluation:** Run Chaos Mesh scenarios on Azure. Measure MTTR (Mean Time To Recovery), Detection Accuracy, and Explanation quality.

---

## 4. Evaluation Metrics & Goals

| Metric | Target |
|---|---|
| **Detection F1-Score** | ≥ 0.90 on simulated faults |
| **MTTR** | < 60 seconds to resolve a fault (vs. manual intervention) |
| **False Positive Rate** | < 5% during clean baseline operation |
| **System Overhead** | < 10% additional resource usage from the agent stack |
| **Agent Agreement** | Track how often RL and LLM agents choose the same action |

## 5. Deployment Topology

The system will run locally on a single machine utilizing an RTX 5060 (8GB VRAM) and 32GB RAM.
- **Local LLM:** A 7B or 8B parameter model (e.g., LLaMA-3 8B or Mistral) running via Ollama will comfortably fit in 8GB VRAM for the LLM Agent.
- **RL Training:** Handled by the CPU/GPU via PyTorch.
- **Later Stage:** The K8s cluster will be shifted to Azure AKS, while the control plane / agents can either be dockerized and deployed to Azure, or run locally pointing to the remote AKS cluster.
