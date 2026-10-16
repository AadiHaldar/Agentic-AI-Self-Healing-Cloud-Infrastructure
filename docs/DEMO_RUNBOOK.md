# AgentHeal — project review demo runbook

**One-sentence pitch:** *Two feedback loops on one platform — a pull-request reviewer that blocks and fixes insecure code
before it merges, and a runtime agent that detects, explains, simulates and then fixes cluster faults.*

Length: **~14 minutes** plus questions. Everything you click is wired to a real backend; where something is a dry run or a
fallback, the console says so on screen. Use that — it is your honesty story.

---

## 0. Where it runs

| | URL | Notes |
|---|---|---|
| **VM1 (deployed copy)** | `http://127.0.0.1:8001` after you open the tunnel | systemd service `agentic-ai`, bound to localhost on purpose (the API has no auth) |
| **Your laptop** | `http://127.0.0.1:8000` | has your `.env`, so **live Gemini** works |
| AKS (other session) | `http://20.255.127.152` | `/api/status` works; **`/` shows `{}`** and `/api/service-health` 404s until the image is rebuilt with the new UI. Show `kubectl get pods -A`, not this page. |

Open the tunnel to VM1 (leave the window open):

```bash
ssh -i collaborator_key -N -L 8001:127.0.0.1:8000 collaborator@20.244.17.209
```

**Gemini on VM1:** no key was copied there (the box is shared). Without it the LLM agent returns a canned plan, labelled
`fallback` in the UI. To get live Gemini on VM1:

```bash
ssh -i collaborator_key collaborator@20.244.17.209
echo 'GEMINI_API_KEY=your_key_here' | sudo tee /etc/agentic-ai.env && sudo chmod 600 /etc/agentic-ai.env && sudo systemctl restart agentic-ai
```

**Recommendation:** do the live run on your **laptop** (`:8000`, live Gemini) and show VM1 as the deployment evidence
(Overview + System pages + `systemctl status`). Or add the key to VM1 and run everything there.

## 1. Pre-flight (do this 30 minutes before, and again 5 minutes before)

- [ ] Laptop server up: `python -m uvicorn dashboard.backend.main:app --host 127.0.0.1 --port 8000` (from the project folder, `PYTHONPATH=.`)
- [ ] Tunnel up: `curl http://127.0.0.1:8001/api/meta` returns JSON.
- [ ] `http://127.0.0.1:8000/api/meta` shows `"gemini_configured": true`.
- [ ] **Reset the twin** (Self-Healing → *Reset twin*). The cluster pill in the top bar must read *healthy*.
- [ ] Do **one** throw-away run of the deadlock scenario to warm up SHAP and Gemini, then *Reset twin* again.
- [ ] Open **PR Review** once while online. GitHub's unauthenticated API allows 60 calls/hour/IP; results are cached
      for 10 minutes, so avoid refreshing repeatedly. On shared venue Wi-Fi someone else may have used the quota — if you
      see the rate-limit notice, open the PRs in GitHub tabs instead (have #11 and #12 open in advance).
- [ ] Browser zoom 100–110 %, dark theme, window ≥ 1280 px wide. Close other tabs.
- [ ] Run the scripted end-to-end check once (section 7). It must end with `15/15 checks passed`.
- [ ] Have `docs/CODEBASE_CHANGES.md` open in a tab for the limitations question.

## 2. Script

### 0:00 — Problem (1 min)
"Outages come from two places: bad code that gets merged, and running services that degrade. Kubernetes' autoscaler only
looks at CPU and memory; if a pod deadlocks, adding replicas just moves the load onto the database. We built one platform
that closes both loops."

### 1:00 — Overview (1 min) · `#/overview`
- Point at the two rows: **Shift-left (code)** and **Shift-right (cluster)**. "Each box is a page; I'll click through them."
- Point at the top bar pills: *Gemini connected*, *no cluster (dry-run)*, *demo dataset*. "The console never pretends — if the
  LLM key is missing or there's no cluster attached, it says so."

### 2:00 — Shift-left: Security Scanner (3 min) · `#/scanner`
1. *Vulnerable code* is preloaded. Click **Scan**. → **Grade F, 9 findings, 6 of 10 categories**, instant.
   Scroll the findings: SQL injection (f-string), `shell=True`, `pickle.loads`, `eval`, MD5, SSRF (`verify=False`), unsafe YAML.
   "This is the same auditor that runs on every pull request. It parses the Python AST — nothing is executed."
2. Click **Fixed code** → Scan → **clean / would pass the merge gate**.
3. Click **Vulnerable deps** → Scan → dependency CVE findings (A06) for `pyyaml==5.3`, `requests==2.28.0`.
4. Say the limitation yourself (it's on screen): *pattern/AST matching, not taint analysis; secrets are covered by detect-secrets in the PR pipeline.*

### 5:00 — Shift-left: PR Review and Auto-Fix (2 min) · `#/review`, `#/autofix`
- **PR Review** lists the real pull requests from GitHub. Select **#11** (the deliberately vulnerable checkout service):
  the bot's review shows OWASP grade F and "Merge blocked". Select **#12**: the auto-fix PR.
- **Auto-Fix** shows the flow (PR opened → audit → gate blocks → fix branch → fix PR) and the real fix PRs with +/− line counts.
- ⚠ **Be accurate about #11/#12.** The review *comment text* on those two PRs was posted by our demo scripts
  (`scripts/deploy_live_owasp_pr.py` etc.), using numbers from the same OWASP auditor. Say: *"For the demo we staged these
  two PRs with scripts that call the auditor and post the result; the production path is the webhook, which I'll show in the
  System page."* Don't say the comments were generated autonomously. Also, #11 and #12 have **no real check run** on GitHub,
  and the two bot comments on each PR quote different counts — don't open them line by line.
- Real, verifiable evidence of the gate: PR **#10** shows **gate passed** and PR **#5/#3** show **gate blocked** (real check runs).

### 7:00 — Shift-right: Self-Healing (6 min) · `#/healing`
1. **Reset twin.** Top bar: cluster *healthy*.
2. Pick **Healthy control** → *Inject & analyse*. → Detect = **Normal**, RL/LLM = `DO_NOTHING`, LLM *skipped*.
   "A system that fires on healthy traffic is useless, so I show the control first."
3. Pick **Thread deadlock** → *Inject & analyse* (the Gemini call takes ~5–10 s; talk through the pipeline while it runs):
   - **Detect** — Isolation Forest flags it, with the raw score (below 0 = anomalous). Measured: a few ms.
   - **Explain** — KernelSHAP: which signal drove it (CPU/latency/memory). Positive (red) = toward anomaly.
   - **Decide** — Q-learning policy vs. the Gemini ReAct agent. They may **agree or diverge**; both are shown, with real latencies
     (RL ≈ 1 ms, LLM ≈ 5–10 s). Badge says *live Gemini* (or *fallback* if no key).
   - **Gate (SimPy)** — the digital twin simulates the **chosen** action on the target and its neighbours and returns SAFE/RISK
     with the predicted CPU shown on the topology ("after action: CPU …"). "Nothing touches the cluster unless this says SAFE."
   - **Act** — *Plan only*. The *Execute* checkbox is disabled because no Kubernetes API is reachable from this server
     (the top bar says *no cluster (dry-run)*); with a cluster attached it runs only the gated plan.
4. Open **LLM reasoning**: root cause + the agent's explanation. Open **SHAP**.
5. Pick **Memory leak** (CPU low, memory 94 %) → the top SHAP feature flips to **memory_usage**. "Same model, different cause,
   different explanation — that's why we explain instead of just alerting."
6. Show **Run history** (each run with RL/LLM/gate/compute time) and, briefly, **Operator override** (confirmation dialog, dry run).

### 13:00 — System and deployment (1 min) · `#/system`
- Real facts from `/api/meta`: model trained, Gemini connected, kubectl live or dry-run, webhook router mounted.
- Webhook pipeline: HMAC-SHA256 constant-time verification, delivery-ID de-duplication, per-installation rate limit.
- Deployment: show `systemctl status agentic-ai` on VM1 (via the tunnel session) and `kubectl get pods -A` for AKS.

### 14:00 — Limitations and what's next (1 min)
Say these before they are asked (all are in `docs/CODEBASE_CHANGES.md`): the twin is a simple what-if model, not a full queueing
simulator; the anomaly data is synthetic; the AST auditor is pattern-based; no authentication yet on the control API; evaluation
needs to be re-run on real traffic and against a measured HPA baseline.

---

## 3. Numbers you can say out loud (measured on this build)

| Stage | Typical | Where it comes from |
|---|---|---|
| Isolation Forest verdict | **~5–25 ms** | `timings.detect_ms` in the response |
| KernelSHAP | **~10–35 ms** | `timings.shap_ms` |
| Q-learning decision | **~1 ms** | `timings.rl_ms` |
| Gemini ReAct decision | **~5–10 s** | `timings.llm_ms` (live Gemini) |
| OWASP scan of a file | **milliseconds** | Scanner page round-trip |
| Test suite | **51 pass** (laptop and VM1) | `pytest tests agentic_engine/tests` |

**Do not quote** the paper's 2.26 ms detection, 2.98 s MTTR, 98 % improvement, 59/60 agreement, or 98.5 % precision. They are
not backed by the code (see CODEBASE_CHANGES B1). If asked: "those figures came from an earlier harness; we have since found
it was falling back to fixed values and are re-running it — the live console shows the real timings."

## 4. Questions you should expect

| Question | Honest answer |
|---|---|
| Is the LLM actually deciding? | When *live Gemini* shows, yes: it receives the SHAP summary and twin verdict and returns JSON. Until today the model names in the code were retired, so it silently used a canned plan; that is fixed and the console now labels the source. |
| What stops the AI from doing something dangerous? | Plan-only by default; execution needs an explicit flag, is gated by the twin, validated names (`shell=False`, RFC-1123 regex), replica bounds 0–100, and an operator override needs confirmation. |
| Is the twin a real simulator? | It is a discrete-event SimPy model with fixed action effects (restart ×0.25, scale ×0.4, patch ×0.65) and dependency stress. It is a safety heuristic, not a calibrated queueing model; the paper's M/M/c wording overstates it. |
| How was it evaluated? | Four synthetic fault patterns on synthetic telemetry; no production traffic and no measured baseline. The paper's table is being re-generated. |
| Why do RL and LLM disagree? | In the recorded run they agreed on **0 of 4** faults. The RL policy always proposes `RESTART_POD` for an anomaly: its Q-table starts from a hand-set prior and is not trained offline, and it is epsilon-greedy. The LLM varies by fault (scale-up for CPU saturation, patch limits for the memory leak). Disagreement is surfaced, not hidden; a trained policy and arbitration are future work. Do not call the RL agent "learned". |
| False-positive rate? | Contamination is 5 %, so roughly 5–6 % of healthy samples are flagged (measured 5.0 % / 6.6 %). |
| Does the PR bot really block merges? | Through a GitHub Check Run named `review-agent/quality-gate` — see real examples on PRs #10 (passed) and #5/#3 (blocked). The OWASP score alone does not yet block; that is a known gap. |
| Where is it deployed? | VM1 (Ubuntu 24.04, systemd) and an AKS cluster with Online Boutique. kubectl actions on VM1 are dry runs. |
| Secrets / security? | HMAC webhook verification, short-lived RS256 App tokens, `.env` never committed. Known gaps: unauthenticated control API (bound to localhost on VM1), listed in CODEBASE_CHANGES section C. |

## 5. If something goes wrong

| Symptom | Fix |
|---|---|
| Top bar says **API offline** | Server stopped. Laptop: restart uvicorn. VM1: `sudo systemctl restart agentic-ai`. |
| Tunnel dead (`curl :8001` hangs) | Re-run the `ssh -N -L …` command. |
| Gemini slow or pill says *fallback* | Say "the model call is the slow stage, ~5–10 s". If it says fallback, the key is missing/invalid: check `/api/meta`. The rest of the pipeline still demonstrates. |
| PR Review shows a rate-limit notice | Open #11 / #12 in GitHub tabs instead; carry on. |
| Twin is already hot / cluster *degraded* | Self-Healing → **Reset twin**. |
| Blank page | Hard refresh (Ctrl+F5); confirm `/api/meta` responds. |

## 6. Cheat sheet

```bash
# VM1 status / logs
ssh -i collaborator_key collaborator@20.244.17.209 'systemctl status agentic-ai --no-pager | head -12; journalctl -u agentic-ai -n 20 --no-pager'

# Redeploy UI after a rebuild (from the project folder)
cd dashboard/frontend-vite && npm run build && cd ../.. && tar czf - dashboard/frontend-vite/dist | ssh -i collaborator_key collaborator@20.244.17.209 'tar xzf - -C /opt/agentic-ai'

# Run the tests
PYTHONPATH=. python -m pytest tests agentic_engine/tests -q

# Direct API calls (same as the UI)
curl -s -X POST http://127.0.0.1:8000/api/evaluate -H 'Content-Type: application/json' \
  -d '{"target_service":"cartservice","cpu_usage":0.99,"mem_usage":0.85,"latency_ms":5000,"request_rate":0}'
```

## 7. End-to-end scripted run

`scripts/demo_e2e.py` drives the whole platform through its public API in about **25 seconds** (or ~13 s without live Gemini),
narrating each step, and **exits non-zero if any check fails** — so it is both a demo and a smoke test. Use it as your opening
("here is the whole system in one run, then I'll show it in the console") or as your safety net if the UI misbehaves.

```bash
# laptop server running on :8000 (live Gemini):
python scripts/demo_e2e.py --base http://127.0.0.1:8000

# VM1 through the tunnel (webhook secret is on the VM; it is never printed here):
export DEMO_WEBHOOK_SECRET="$(ssh -i collaborator_key collaborator@20.244.17.209 "sudo grep '^GITHUB_WEBHOOK_SECRET=' /etc/agentic-ai.env | cut -d= -f2")"
python scripts/demo_e2e.py --base http://127.0.0.1:8001
```

| Step | What it proves | Checks |
|---|---|---|
| 0 Platform | what the deployment is wired to (Gemini, cluster, model) | API up, model trained, twin healthy |
| 1 Shift-left | vulnerable code → grade F and blocked; fixed code → A+ and passes; CVE pins found | 3 |
| 2 Webhook | unsigned → 401, wrong signature → 401, signed → 200, replay ignored | 4 |
| 3 Shift-right | healthy control stays quiet; four faults are flagged with SHAP, RL vs LLM, SimPy verdict and **measured** timings | 6 |
| 4 Act | execution is gated; reports honestly when no cluster is reachable | 1–2 |

A recorded run is in `docs/DEMO_E2E_SAMPLE_OUTPUT.txt` (15/15 passed, live Gemini). Say plainly what step 2 does **not** cover:
the GitHub App's webhook points at the production deployment, so a real "open a PR → bot reviews it" round-trip is not exercised
by this script.

### Optional: real actuation on a live cluster (only if you have time to set it up)

The console and API will execute a gated plan only when a cluster is reachable (top bar shows `cluster: <context>`).

- **Local kind cluster** (`kind-boutique-cluster` is in your kubeconfig): start Docker Desktop, wait for the cluster to come back
  (`kubectl get pods -A`), then start the laptop server with the namespace the manifests use:
  ```bash
  K8S_NAMESPACE=online-boutique PYTHONPATH=. python -m uvicorn dashboard.backend.main:app --host 127.0.0.1 --port 8000
  ```
  In **Self-Healing** tick *Execute on the cluster if the twin says SAFE*, run **Flash-sale surge**, then show the result with
  `kubectl get deploy checkoutservice -n online-boutique` (replicas change when the plan is `SCALE_UP`) and `kubectl get pods -n online-boutique`.
  Or run `python scripts/demo_e2e.py --execute`.
- **AKS** needs `az aks get-credentials` on the machine running the server and `K8S_NAMESPACE=default` (the Boutique there is in
  `default`). Only do this if you have rehearsed it; the actions change a real cluster.
- Rehearse once before the review. If the cluster is not reachable on the day, the dry-run demo above is complete on its own.

---

## 8. Live PR review on GitHub (the real webhook path)

This is the real thing: a pull request opened on GitHub is delivered by webhook (through the smee.io relay) to your laptop, reviewed by
the pipeline, and the results are posted back by the GitHub App `agentic-review-agent-73886`. It was rehearsed end to end on PR #13.

**Start (about 20 s):**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\live_demo.ps1
```

It opens two terminal windows (leave both visible: **RELAY** and **AGENTHEAL SERVER**), the console, and the GitHub
"Open a pull request" form for branch `demo/live-review`. Check the READY block says *Gemini connected: True* and
*PR-review webhook: True*, and the relay window says *Connected to https://smee.io/…*.

**What you do and say:**

| Step | Action | What to point at |
|---|---|---|
| 1 | In the GitHub tab, click **Create pull request** (title e.g. "Add payment service"). The branch adds one deliberately vulnerable file. | "A developer opens a PR. Nothing else is triggered by me." |
| 2 | Switch to the **AGENTHEAL SERVER** window. Within a second you see `Received event: pull_request`. | "GitHub just called our webhook; the signature was verified." |
| 3 | Watch the log: `Static analysis: N findings across 5 tools` → `LLM review: …` (the slow one, ~25 s) → `Test gap detection` → `Posted PR summary comment` → `Posted inline review with N comments` → `Check Run created: conclusion=failure`. | "Ruff, Bandit, detect-secrets, pip-audit, then Gemini, then the AST test-gap check." |
| 4 | On the PR page: the **summary comment** (verification matrix, OWASP grade), then **Files changed** for the inline comments with severity, then the **Checks** tab: `review-agent/quality-gate` ✗. | "Merge is blocked by a real GitHub check, not a label." |
| 5 | Add a comment: `@review-bot what is the most dangerous issue here and how do I fix it?` and wait ~30 s. | The bot answers using the actual diff, with a code fix. |

Total time from *Create pull request* to the failing gate is **about 70 seconds** (measured). Fill the Gemini wait with step 4's explanation
of the pipeline matrix, or have the PR page open on **Files changed** and refresh.

**Safety net (if the live run fails or is slow):** PR **#13** is the rehearsal of exactly this flow, with the full review, 23 inline
comments and the failing check. Open it and say "this is the same run from earlier". Also PR #11/#12 for the fix-PR story (their comments
were script-posted, see section 2).

**If nothing happens after opening the PR:**
1. Is the RELAY window printing `POST … - 200` lines? If not, restart it (re-run the script).
2. GitHub → *Settings → Developer settings → GitHub Apps → agentic-review-agent-73886 → Advanced → Recent deliveries* → click the
   `pull_request` delivery → **Redeliver**.
3. Or close and **Reopen** the PR (a `reopened` event also triggers a full review).

**Caveats to state if asked:** the laptop must be online and running both windows; the relay (smee.io) is a third-party forwarder, but every
request is HMAC-verified so a forged request is rejected (401); only the App's installation on this one repository can post. The first
review of a PR includes a ~27 s Gemini call, and each posting step to GitHub takes several seconds.

**After the demo:** close the demo PR in GitHub (do not merge it); stop the two terminal windows.

