# 🎓 FINAL PRE-PRESENTATION MASTER REVISION CHEAT SHEET
**Project Title:** *Agentic AI-Driven Self-Healing Cloud Infrastructure (AgentHeal)*  
**Authors:** Aadi Haldar (CB.SC.U4AIE24201), Raghuram Sekar, Aaditya Paul, Shravan Rajesh Menon  
**Affiliation:** Dept. of AI & Engineering, Amrita Vishwa Vidyapeetham, Coimbatore, India  

---

## ⚡ 1. THE 30-SECOND ELEVATOR PITCH (Opening Statement)
> *"Good morning, Professors. Distributed cloud systems face two major sources of downtime:*  
> *1. **Code Delivery Failures:** $62\%$ of production outages stem from vulnerable, untested code slipping through pull requests.*  
> *2. **Slow Runtime Recovery:** When live Kubernetes microservices crash, manual MTTR averages **45 minutes**.*  
>  
> *Our project, **AgentHeal**, presents a unified, closed-loop Agentic AI platform with two synchronized engines:*  
> *• **Shift-Left Engine (Product A):** Intercepts GitHub PRs, runs an 11-stage AST + SAST security audit, blocks bad merges via Quality Gates, and generates 1-click auto-fix PRs in **$14.2\text{ s}$**.*  
> *• **Shift-Right Engine (Product B):** Streams 4D telemetry from live Kubernetes clusters, detects anomalies with Isolation Forest in **$2.26\text{ ms}$**, explains root-causes with KernelSHAP, arbitrates between SimiFed Federated RL and Gemini ReAct, and validates fixes via a **$0.01\text{ s}$ SimPy Digital Twin Safety Gate** before real physical actuation.*  
> *We deployed the global control plane on **Microsoft Azure Container Apps** and evaluated runtime resilience on the **CNCF Google Online Boutique** benchmark."*

---

## 📊 2. DATASETS & BENCHMARK TRACES (Crucial Defense Topic)

If professors ask: *"Where did you get your data from?"* or *"What did you train this on?"*

| Dataset / Benchmark | Size / Scope | Source & Characteristics | Where Used in Project |
|---|---|---|---|
| **Google Online Boutique (CNCF)** | 10 Microservices (gRPC/REST), 4 evaluated directly (`frontend`, `checkoutservice`, `cartservice`, `redis-cart`) | Standard Cloud Native Computing Foundation benchmark for distributed e-commerce architecture | Runtime Kubernetes cluster testbed for physical scaling, restarts, and limit patching |
| **Alibaba Cloud Cluster Trace Distribution** | $10,000+$ synthetic telemetry intervals | Simulated 4D metric distributions $[\text{CPU}, \text{RAM}, \text{Latency}, \text{Throughput}]$ mimicking real-world cloud workloads | Pre-training the Isolation Forest anomaly detector & SimiFed baseline centroids |
| **Synthetic Pull Request Audit Corpus** | 50 Curated PRs across 4 defect classes | Injected with SQLi (Bandit B608), Leaked Secrets (Stripe/AWS), AST Test Gaps, and Async Blocking I/O (Ruff) | Evaluating Shift-Left detection precision ($98.5\%$) and recall ($97.5\%$) |
| **SimPy Discrete-Event Trace Sim** | Continuous $M/M/c$ Queuing Generator | Poisson arrivals ($\lambda=500\text{ req/s}$), Exponential service ($\mu=150\text{ req/s/core}$) | Dry-run pre-execution safety gate to guarantee $\rho < 0.95$ and $\hat{U} < 80\%$ |

---

## 🏛️ 3. DUAL-ENGINE ARCHITECTURE (How Both Sides Connect)

```
                            THE AGENTHEAL CLOSED-LOOP ARCHITECTURE

  ┌────────────────────────────────────────────────────────┐   ┌────────────────────────────────────────────────────────┐
  │         PRODUCT A: SHIFT-LEFT (PRE-MERGE PR)           │   │       PRODUCT B: SHIFT-RIGHT (RUNTIME K8S ENGINE)      │
  ├────────────────────────────────────────────────────────┤   ├────────────────────────────────────────────────────────┤
  │ 1. Developer opens PR on GitHub                        │   │ 1. Telemetry Stream: 4D Vector X_t every 5.0s          │
  │ 2. Webhook triggers Azure Container App (HMAC-SHA256)   │   │ 2. Isolation Forest: Anomaly Score in 2.26 ms (MTTD)   │
  │ 3. Static Security: Bandit SAST (SQLi B608)            │   │ 3. KernelSHAP: Game-Theoretic Root-Cause Attribution   │
  │ 4. Secrets Scan: Detect-Secrets (Stripe/AWS Keys)      │   │ 4. Multi-Agent Arbitration:                            │
  │ 5. Compiler Grammar: Python AST Test Gap Detector      │   │    • SimiFed RL (3.10ms Reflex, Cosine Similarity)     │
  │ 6. Call-Graph: AST Import Walker -> Mermaid Diagram    │   │    • Gemini 2.0 Flash (412ms ReAct Chain-of-Thought)   │
  │ 7. Performance: Ruff (Blocking Sync I/O in Async)      │   │ 5. SimPy Digital Twin: 0.01s M/M/c Queuing Safety Gate │
  │ 8. LLM Reasoning: Gemini ReAct Auto-Fix Generator      │   │ 6. Physical Actuation: kubectl scale / restart / patch │
  │ 9. Quality Gate: Check Run Blocks Merge (Red X)        │   │ 7. Feedback Loop: Telemetry returns to healthy state   │
  │ 10. Auto-Fix PR Opened (PR #10 -> Green Check Mark)    │   │                                                        │
  └────────────────────────────────────────────────────────┘   └────────────────────────────────────────────────────────┘
```

---

## 📐 4. ALL EXACT MATHEMATICAL FORMULATIONS

| Stage | Model / Algorithm | Exact Mathematical Formula | Purpose & What to Explain |
|---|---|---|---|
| **1. Telemetry** | 4D Metric Vector | $\vec{X}_t = \big[\text{CPU}_t, \text{RAM}_t, \text{Latency}_t, \text{Rate}_t\big] \in \mathbb{R}^4$ | Normalizes multi-dimensional telemetry every 5.0s |
| **2. Anomaly Detection** | Isolation Forest | $s(\vec{X}_t, n) = 2^{-\frac{E(h(\vec{X}_t))}{c(n)}}, \quad c(n) = 2H(n-1) - \frac{2(n-1)}{n}$ | $s < 0 \implies$ Anomaly. Faster path isolation means fewer cuts needed to isolate defect |
| **3. Root Cause** | KernelSHAP | $\phi_i(v) = \sum_{S \subseteq F \setminus \{i\}} \frac{\|S\|!(\|F\|-\|S\|-1)!}{\|F\|!} [v(S \cup \{i\}) - v(S)]$ | Computes Shapley game-theoretic marginal contribution for each metric ($\phi_{\text{CPU}} = +0.82$) |
| **4. RL State Matching** | SimiFed Cosine Metric | $\text{CosSim}(\vec{X}_t, \vec{B}_k) = \frac{\vec{X}_t \cdot \vec{B}_k}{\|\vec{X}_t\|_2 \|\vec{B}_k\|_2} = 0.978$ | Discretizes continuous metrics into historical failure centroids for instant 3.1ms Q-table lookup |
| **5. RL Optimization** | Tabular Q-Learning | $Q(s, a) \leftarrow Q(s, a) + \alpha [R + \gamma \max_{a'} Q(s', a') - Q(s, a)]$ | Reinforcement learning policy update ($\alpha=0.1, \gamma=0.95$) |
| **6. Safety Gate** | $M/M/c$ Queuing Headroom | $\rho = \frac{\lambda}{c \cdot \mu} = \frac{500}{4 \cdot 150} = 0.833 \quad (< 1.0 \text{ Stable})$ | SimPy pre-execution check: guarantees scaling will not trigger queue explosion |
| **7. Post-Fix CPU** | Capacity Scaling | $\hat{U}_{\text{post}} = \frac{U_{\text{pre}} \cdot c_{\text{curr}}}{c_{\text{new}}} = \frac{95.4\% \times 1}{4} = 23.8\%$ | Predicts post-remediation headroom before executing `kubectl` |
| **8. Availability** | High-Availability Form. | $A = \frac{\text{MTTF}}{\text{MTTF} + \text{MTTR}} = \frac{720\text{h}}{720\text{h} + 8.28 \times 10^{-4}\text{h}} \approx 99.9999\%$ | **Theoretical upper bound** (Six Nines) based on 2.66s MTTR vs assumed 720h MTTF |

---

## 📈 5. EXPERIMENTAL RESULTS SUMMARY (With Real Statistics)

### A. Runtime Failure Scenarios ($N=15$ Repeated Trials per Scenario)
* **Mean Detection Latency (MTTD):** $2.26 \pm 0.37\text{ ms}$ across all scenarios.
* **RL Reflex Latency:** $3.10 \pm 0.42\text{ ms}$.
* **Gemini LLM Reasoning Latency:** $412 \pm 68\text{ ms}$ (higher variance due to API network round-trip and non-deterministic decoding).
* **SimPy Safety Gate Validation:** $10.1 \pm 0.8\text{ ms}$ ($0.01\text{ s}$).
* **End-to-End MTTR:**
  * S1 (Flash Sale Spike): $2.66 \pm 0.18\text{ s}$
  * S2 (Thread Deadlock): $3.12 \pm 0.24\text{ s}$
  * S3 (Memory Leak): $2.89 \pm 0.20\text{ s}$
  * S4 (Cascading Overload): $3.25 \pm 0.30\text{ s}$
  * **Overall Mean MTTR:** $\mathbf{2.98 \pm 0.23\text{ s}}$

### B. Shift-Left PR Audit Performance ($n=50$ PRs)
* **SQL Injection (Bandit B608):** $100\%$ Precision, $100\%$ Recall ($50/50$ True Positives, $0$ False Positives).
* **Hardcoded Secrets (Detect-Secrets):** $96.0\%$ Precision, $100\%$ Recall ($50/50$ TP, $2$ FP).
* **AST Test Gaps:** $100\%$ Precision, $96.0\%$ Recall ($48/50$ TP, $0$ FP).
* **Blocking Async I/O (Ruff):** $98.0\%$ Precision, $94.0\%$ Recall ($47/50$ TP, $1$ FP).
* **Overall PR Audit Precision:** $\mathbf{98.5\%}$, **Recall:** $\mathbf{97.5\%}$, **Audit Duration:** $\mathbf{14.2\text{ s}}$.

---

## ☁️ 6. CLOUD DEPLOYMENT & DEVOPS ARCHITECTURE

* **Cloud Provider:** Microsoft Azure (Region: `East Asia`).
* **Resource Group:** `rg-agentic-app-prod`.
* **Compute Platform:** Azure Container Apps (`pr-review-agent`, currently on immutable revision `v19`).
* **Container Registry:** Private Azure Container Registry (`acragenticai27215.azurecr.io`).
* **IaC Engine:** Terraform with `azurerm` v3.90 provider ([`infrastructure/terraform/azure/main.tf`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/infrastructure/terraform/azure/main.tf)).
* **Docker Multi-Stage Strategy:**
  * Stage 1 (`node:20-alpine`): Compiles React + Vite Single Page Application.
  * Stage 2 (`python:3.11-slim`): Copies compiled bundle, installs FastAPI/Gemini/SimPy/Bandit ($\text{Image Size} < 400\text{MB}$).
* **FinOps / Serverless Autoscaling:** KEDA scale-to-zero (0 idle replicas = $\$0.00$ cost; spins up in $3.5\text{s}$ cold start upon incoming webhook).
* **Security & Auth:** HMAC-SHA256 webhook signature verification + RS256 asymmetric JWT for GitHub App installation access tokens.
* **Live Cloud URL:** `https://pr-review-agent.wonderfulflower-41d6d2a5.eastasia.azurecontainerapps.io`

---

## 🎬 7. LIVE DEMONSTRATION PLAYBOOK (Step-by-Step)

### Step 1: Show Cloud Presence (Azure Portal)
1. Open Azure Portal tab.
2. Show **`Resource visualizer`** (proves Terraform topology).
3. Show **`Revisions and replicas`** (shows immutable revisions `v1` to `v19` and KEDA scale-to-zero).

### Step 2: Show Shift-Left Prevention (GitHub PR #9 & #10)
1. Open **[PR #9](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pull/9)**:
   * Show the **interactive Mermaid architecture diagram**.
   * Show the **11-stage audit matrix**.
   * Show the **Red ❌ Failed Quality Gate Check Run**.
   * Show the **`@review-bot` comment thread** explaining the SQL injection vulnerability.
2. Show **[Auto-Fix PR #10](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pull/10)**:
   * Show parameterized query fix + unit tests.
   * Point out the **Green ✅ Passing Quality Gate**.

### Step 3: Show Shift-Right Runtime Healing (CLI + Web UI)
1. Open terminal and run:
   ```powershell
   python scripts/demo_interactive_chaos.py
   ```
2. Choose Option `[1]` (Flash Sale Spike) or Option `[4]` (All Scenarios).
3. Point to the **Unicode math formula callout boxes** rendering live on screen.
4. Show the active `kubectl` pod table scaling from 1 to 4 replicas in 5 seconds.
5. In browser (`http://localhost:8000`), show the **5-step animated pipeline tracker** and **KernelSHAP horizontal bar graphs**.

---

## 🛡️ 8. TOP 10 TOUGH VIVA / DEFENSE QUESTIONS & BULLETPROOF ANSWERS

| # | Question from Professor / Reviewer | Your Bulletproof 2-Sentence Answer |
|---|---|---|
| **1** | *"Why do you need both an RL Agent and an LLM?"* | *"SimiFed RL provides sub-5ms reflex speed for known failure signatures, while Gemini ReAct provides semantic reasoning and root-cause explanations for novel edge cases. Together with our SimPy safety gate, they prevent single-agent hallucinations or policy drift."* |
| **2** | *"How is AST parsing superior to standard Regex matching?"* | *"Regex merely searches for string patterns and produces high false positives on comments or documentation strings. Python AST parses the actual compiler grammar, inspecting abstract syntax nodes with 100% syntactic precision."* |
| **3** | *"Why not just rely on standard Kubernetes HPA (Horizontal Pod Autoscaler)?"* | *"HPA is reactive and threshold-bound (e.g. CPU > 80%) with no semantic context. It cannot differentiate between a legitimate traffic spike vs. a thread deadlock or memory leak, cannot run digital-twin dry-runs, and cannot fix code."* |
| **4** | *"Is your Six Nines (99.9999%) availability empirically measured?"* | *"No, we explicitly report that as a theoretical upper bound derived from $A = \text{MTTF}/(\text{MTTF}+\text{MTTR})$ assuming a 720h MTTF. True empirical availability would require months of continuous production telemetry."* |
| **5** | *"Why are your baseline MTTR comparisons (HPA/Keptn) footnoted as contextual?"* | *"To maintain academic integrity, we footnote that HPA and Keptn numbers are taken from published literature and DORA reports rather than co-measured on the exact same laptop hardware under identical injections."* |
| **6** | *"How does the SimPy Safety Gate prevent cluster crashes?"* | *"SimPy runs a 10ms discrete-event $M/M/c$ queuing simulation before any `kubectl` command executes, verifying that traffic intensity $\rho = \frac{\lambda}{c\mu} < 0.95$ and post-scale CPU drops below 80%."* |
| **7** | *"How does SimiFed RL discretize continuous cluster telemetry?"* | *"It computes the Cosine Similarity between the incoming 4D vector $\vec{X}_t$ and historical baseline centroids $\vec{B}_k$. The argmax similarity maps continuous metrics into discrete Q-table states."* |
| **8** | *"How do you handle LLM latency variance and non-determinism?"* | *"Table III in our paper explicitly documents Gemini latency variance ($412 \pm 68\text{ ms}$). In production, the RL agent acts as the low-latency fast-path fallback if the LLM exceeds a predefined timeout threshold."* |
| **9** | *"Where are cloud secrets and private keys stored?"* | *"All sensitive credentials (GitHub App RSA private key and Gemini API token) are injected via Azure Container App secret references into environment variables, never hardcoded in git."* |
| **10** | *"Can this system be deployed on AWS or GCP instead of Azure?"* | *"Yes! All infrastructure is defined in modular Terraform HCL and all application components are packaged into standard OCI Docker containers, making the architecture 100% cloud-agnostic."* |

---

### 📄 Document Reference:
* **Compiled PDF Paper:** `C:\Users\aadih\Desktop\AgentHeal_Paper.pdf`
* **LaTeX Source:** `docs/paper/paper.tex`
* **Raw Evaluation Metrics:** `docs/paper/eval_results.json`
* **Live Cloud App:** `https://pr-review-agent.wonderfulflower-41d6d2a5.eastasia.azurecontainerapps.io`
