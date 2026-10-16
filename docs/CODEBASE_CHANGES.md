# AgentHeal — codebase change list

Status of every change the analysis found. **Done** items were made in this session and are covered by the existing
tests (51 pass locally and on VM1). Everything else is open.

Legend: 🔴 fix before you submit or claim it · 🟠 fix soon · 🟡 nice to have

---

## A. Done in this session

| # | Change | Where |
|---|---|---|
| A1 | **Gemini model names were all retired.** `llm_agent.py` tried `gemini-2.5/1.5/2.0-flash`, which now return 404, so the LLM agent *always* used its canned fallback. Now uses `gemini-3.6-flash` (override with `GEMINI_MODEL`). | `agentic_engine/llm_agent.py` |
| A2 | LLM output is labelled with its provenance (`gemini:<model>`, `fallback`, `skipped`) and the UI shows it. | `llm_agent.py`, `orchestrator.py` |
| A3 | **SimPy gate judged the wrong thing.** It vetoed on *any* hot pod in the twin and simulated an action other than the one the LLM chose. Now simulates the chosen action and judges only the target plus its direct neighbours. Unknown target ⇒ `TARGET_NOT_IN_TWIN`, not "safe". | `agentic_engine/tools/simpy_tools.py`, `llm_agent.py` |
| A4 | **`/api/evaluate` actuated twice and bypassed the gate.** It now returns a plan only. `execute=true` actuates the *gated LLM* plan, never the raw RL action. | `dashboard/backend/main.py`, `orchestrator.py`, `llm_agent.py` |
| A5 | The detector is now fed the four real features (cpu, mem, latency, rate) and decides `is_anomaly` itself. Before, latency and rate were faked as `cpu*100` and `mem*200`, which made even a healthy vector look anomalous. | `main.py` |
| A6 | **SHAP signs were inverted** (explained `predict()`, a ±1 step function, where negative means anomalous). Now explains `-decision_function`, so positive always means "toward anomaly". Background is a sample of the real healthy telemetry. | `detection/explainer/shap_explainer.py` |
| A7 | kubectl failures were reported as `"[Simulated] … (Cluster Offline)"` and the API still said `success`. Now `failed` with the real stderr, and `dry_run` when kubectl is not installed. | `agentic_engine/tools/k8s_tools.py` |
| A8 | The Vite console was **never served** (`dashboard/frontend/` won the mount). Order reversed: built Vite UI first, legacy UI as fallback. | `main.py` |
| A9 | New `/api/meta` (what is really configured), `/api/topology/reset`, per-stage `timings` in `/api/evaluate`. Seed topology starts healthy so a demo can create the incident. | `main.py` |
| A10 | Demo seed data is switchable (`SEED_DEMO_DATA=0`) and the UI labels it. | `main.py` |
| A11 | **UI rewritten.** No invented fallback numbers anywhere; offline shows as offline. Review/Auto-Fix read the real PRs and check runs from GitHub. No external fonts/CDNs (works on venue Wi-Fi). | `dashboard/frontend-vite/` |
| A12 | Windows-only native packages moved to `optionalDependencies`, so `npm ci` works in the Linux Docker build. | `dashboard/frontend-vite/package.json` + lock |

---

## B. 🔴 Fix before you submit or claim

### B1. The paper's results table is not measured data
- `scripts/run_evaluation.py` (as committed) raises `TypeError` on its first call (`SHAPExplainer()` has no `model`
  argument). The `except` branch then writes **hardcoded literals** from the script (`mttd 2.18`, `e2e 2.661`, …) into
  `eval_results.json`. Those literals are exactly the numbers in `docs/paper/paper.tex` Table I.
- Your uncommitted version runs for real, but still **adds a constant `+ 2.5` s** to every "MTTR", and keeps the
  fallback dictionary. Real numbers: MTTD ≈ 8 ms (paper 2.26), RL ≈ 0.5 ms (3.14), SimPy ≈ 0.4 ms (10.7).
- **Do:** delete the fallback dict; report compute time and (separately, if measured) actuation time; regenerate the table;
  rewrite the abstract/conclusion numbers (2.26 ms, 2.98 s, "98%").
- The paper's **LLM latency (435 ms)** and **agreement (59/60)** have no source (`consensus_rate` is hardcoded `1.0`).
  Measured Gemini latency is **≈ 5–10 s**, not 2.4 s as the README says.
- The **"98% faster than HPA"** compares against a *cited* 3–5 min, not a measured baseline. Either run HPA on the same
  fault or say "vs. figures reported in the literature".
- **"50 PRs, 98.5% precision / 97.5% recall"**: no code in the repo produces it. Remove, or build the labelled set and run it.
- The scenario harness seeds the twin at 20% CPU for every fault, so its SimPy gate never sees the injected load.

### B2. Paper ↔ code disagreements (a reviewer will find these)
- Paper: **M/M/c queue**, ρ ≥ 0.95, 5% drop rate. Code: deterministic CPU-decay model, `max CPU < 0.90`. Describe what exists.
- Paper γ = 0.95, scrape 5 s. Code γ = 0.9, 15 s.
- Paper: "Q-learning agent and LLM run in parallel", "smaller blast radius wins on disagreement". Code runs them **sequentially**
  and does not arbitrate (it reports `actions_match`).
- SF-DTM cited as "Li et al. 2024" in the paper, "Saxena & Singh 2025" in the README.
- README/paper say PRs **#9/#10**, the repo's demo PRs are **#11/#12**.
- README/paper say "Gemini 2.0 Flash"; code calls `gemini-3.6-flash`.
- README says React 18 / Vite 6; project is React 19 / Vite 8.

### B3. The demo PR threads are scripted, not webhook output
The review comments on PRs #11 and #12 were posted by `scripts/deploy_live_owasp_pr.py`, `deploy_live_owasp_autofix_pr.py`
and `setup_clean_demo_prs.py` from templated strings, under two different accounts. They also disagree with each other
(#11: "9 issues / 6 categories" and "14 / 10"; #12: "70% Grade C … all categories compliant" and "100% A+").
Neither PR has a real `review-agent/quality-gate` check run on its head commit. Do not describe those comments as
autonomously generated by the live pipeline unless you re-run it for real (see B4).

### B4. PR-review static analysis scans the wrong directory
`webhook_handler` calls `run_full_pipeline(repo, pr, sha, token)` without `repo_path`, so ruff/bandit/detect-secrets run in the
**server's working directory** on file names taken from the PR. They analyse whatever is at those paths locally, not the PR's
code. Fix: fetch each changed file's contents at the PR head (or `git clone --depth 1` at the SHA into a temp dir) and pass
that as `repo_path`. Same for `detect_unit_test_gaps`.

### B5. The quality gate ignores the OWASP score
`post_quality_gate_check` receives only static/LLM findings. The OWASP result is appended to the comment but never blocks a
merge, contradicting the paper ("if the score falls below our safety bar, the merge is stopped"). Merge OWASP findings into
`all_findings` or add a score threshold to the gate.

---

## C. 🟠 Security of the service

| # | Issue | Fix |
|---|---|---|
| C1 | `/api/override`, `/api/evaluate`, `/api/github/create-pr`, `/api/learnings/dismiss`, `/api/seed-demo`, `/api/github/webhook` have **no authentication**; CORS is `*` with credentials. | Require a bearer token (`ADMIN_TOKEN`) on mutating routes; restrict CORS to the console origin. |
| C2 | `/api/github/webhook` (legacy) has **no HMAC check**. | Delete it or reuse `_verify_hmac`. |
| C3 | `_verify_hmac` **fails open** when no secret is configured. | Return 401 when the secret is missing in non-dev mode. |
| C4 | `eslint` runs via `npx` in a directory containing PR-supplied config (`eslint.config.js` is executable code). | Run ESLint with `--no-config-lookup` and a bundled config, or in a sandbox. |
| C5 | Startup seeds a hardcoded installation ID, repos and **fabricated review rows** into the real DB; hardcoded ngrok URL in `/api/github/app-config`. | Gate behind `SEED_DEMO_DATA` (done), default it off in production, move URLs to env. |
| C6 | Tests write into the live DB (`PR_REVIEW_AGENT_DB` defaults to the service DB). | Point tests at a temp DB in `conftest.py`. |
| C7 | `.git/config` of the project folder embeds a GitHub **OAuth token** in the `origin` URL. | Revoke it, use Git Credential Manager. |
| C8 | `collaborator_key` (SSH private key) is untracked but **not in `.gitignore`**. | Add it (and `*_key`, `*.pem`) before the next commit. |
| C9 | OWASP rule `os.path.join` ⇒ "path traversal" fires on every call (17 hits in `pipeline.py`); hardcoded secrets are not detected by the auditor. | Only flag when an argument is tainted from a parameter; add a secret rule. |
| C10 | `_validate_k8s_name` uses `$`, which accepts a trailing newline. | Use `\Z` / `fullmatch`. |

---

## D. 🟠 Deployment and infrastructure

| # | Issue | Fix |
|---|---|---|
| D1 | **AKS deployment serves `{}` at `/` and 404s `/api/service-health`** (checked read-only at `http://20.255.127.152`): the image was built with `SKIP_FRONTEND=true` and the PR-review router is not mounted there. | Rebuild with the frontend (A12 makes this possible) and check `/api/meta` after rollout. |
| D2 | `Dockerfile` does not copy `services/` or `scripts/`; `/api/owasp/compliance` returns nothing and the email endpoints raise `ImportError` in the image. | Add the `COPY` lines or remove those endpoints' dependency on scripts. |
| D3 | The AKS image has no `kubectl`, so every action there is a dry run. | Install kubectl and give the pod a ServiceAccount with a scoped Role, or state that it is dry-run only. |
| D4 | `.github/` is gitignored, so the workflow is not in the repo. The workflow uses `secrets.GITHUB_APP_PRIVATE_KEY` / `GITHUB_WEBHOOK_SECRET` — names starting with `GITHUB_` are not allowed. `contains(head_commit.modified, 'dir/')` never matches a directory, so Terraform only runs on manual dispatch. | Rename secrets (`APP_PRIVATE_KEY`…), use `paths-filter`, track the workflow. |
| D5 | Terraform: image is the placeholder quickstart; ingress `target_port = 80` but the app listens on 8000; Postgres provisioned but unused (app uses SQLite on ephemeral disk); ACR admin enabled; Postgres firewall `0.0.0.0`; password defaults to `PLACEHOLDER_SET_VIA_CI`. | Fix port, use managed identity for ACR, remove the unused Postgres or implement the migration, require the password variable. |
| D6 | SQLite on a container with scale-to-zero loses data. | Azure Files mount or the Postgres migration. |
| D7 | `requirements.txt`: `torch` unpinned (use the CPU wheel), two Gemini SDKs. | Pin versions, drop `google-generativeai`. |

---

## E. 🟡 Product B quality

- Isolation Forest `contamination=0.05` flags ~5% of healthy data by construction (measured 5.0% / 6.6% FPR). Report FPR; the
  synthetic anomalies are 5σ+ outside the healthy range, so 100% recall is trivial. Evaluate on a harder or real dataset.
- RL agent: epsilon-greedy (10% random actions) in production, reward is a constant, `Q[s][a]` updates with `next_state == state`.
  Use greedy at inference and a real reward (post-action health from the twin).
- `SimiFedRLAgent` uses cosine similarity to a single fixed baseline; "federated" is a name only. Say so, or implement it.
- Twin state is process-local; `StateSynchronizer` (Prometheus) is never started by the app. Wire it up or drop the claim.
- `PredictiveForecaster` (LSTM) is not used by any request path; the LLM prompt hard-codes "High exhaustion risk within 10 minutes".
- Kubernetes: `restart_pod` force-deletes with `--grace-period=0`; prefer `rollout restart`.

## F. 🟡 Hygiene

- Untracked/committed binaries: `kind.exe` (10 MB, ignored), `Reference.zip` (17 MB), notebook (1 MB), slide PNGs, `~$…pptx` lock file.
- `docs/paper_final` is an extension-less 68 KB untracked file.
- Pin Python 3.12 (the VM) — the local machine runs 3.14 with many deprecation warnings.
- `on_event("startup")` is deprecated; use lifespan.
- Add a smoke test that boots the app and calls `/api/meta`, `/api/evaluate`, `/api/owasp/scan`.
