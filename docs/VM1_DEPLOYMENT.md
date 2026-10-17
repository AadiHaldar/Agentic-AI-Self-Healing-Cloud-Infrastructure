# VM1 deployment

VM1 (`20.244.17.209`, Ubuntu 24.04, Central India, Azure resource group `VM1_group`) runs a complete copy of the platform **in parallel with the laptop**.
The laptop path stays the live one until you switch the GitHub App's webhook (see "Switching").

```
 GitHub ──webhook──► smee.io relay ──► laptop :8000   (live today)
    │
    └─ (after switching) ──► http://20.244.17.209/webhooks/github ──► nginx :80 ──► 127.0.0.1:8000 (agentic-ai, user agentheal)
```

## What is installed

| Piece | Where | Notes |
|---|---|---|
| App code (current `main`) | `/opt/agentic-ai`, built from the clone in `/opt/agentic-src` | updated by `agentheal-deploy` |
| Service | `systemd` unit `agentic-ai` (`infrastructure/vm1/agentic-ai.service`) | runs as the **unprivileged user `agentheal`** (no shell, no sudo); `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=full`, `ProtectHome`; listens on **127.0.0.1:8000 only** |
| Public front door | nginx on port 80 (`infrastructure/vm1/nginx-agentic-ai-webhook.conf`) | forwards only `/webhooks/github`, `/install`, `/api/github/app-callback`; everything else returns `403`, so the unauthenticated control API and the console are **not** exposed to the internet |
| Firewall (NSG `VM1-nsg`) | inbound 22 (SSH) and 80 (HTTP) from anywhere | set by the VM owner |
| GitHub App credentials | `/opt/agentic-ai/.env.app` (owner `agentheal`, mode 600) | App ID, slug, webhook secret, private key |
| Gemini key | `/etc/agentic-ai.env` (owner root, mode 600) | read by systemd, not by the app user directly |
| Database | `/opt/agentic-ai/data/pr_review_agent.db` (SQLite, WAL) | nightly backup at 03:00 to `/opt/agentic-ai/backups` (last 7 kept) by `agentheal-backup` |
| Scanners | Ruff, Bandit, detect-secrets, pip-audit in the venv | used by the PR review pipeline |
| Flags | `SEED_DEMO_DATA=0`, `AUTOFIX_RUN_TESTS=1` | auto-fix runs the tests it generates, as the unprivileged user |

Not present on purpose / not done: no TLS (no domain; GitHub accepts an HTTP webhook URL, the payload is signed with HMAC-SHA256),
no Kubernetes or `kubectl` (so actions are plan-only dry runs), no authentication on the control API (it is only reachable from the VM itself).

## Everyday commands (on VM1)

```bash
agentheal-deploy                                   # pull main, build the console, sync, restart, health-check
sudo systemctl status agentic-ai --no-pager
sudo journalctl -u agentic-ai -f                   # live log: webhook received, scanners, Gemini, posted comments
curl -s http://127.0.0.1:8000/api/meta             # what is configured (Gemini, cluster, model, webhook router)
sudo /usr/bin/python3 /usr/local/bin/agentheal-backup   # manual DB backup
```

From the laptop, open the console through a tunnel (the API is not public):

```powershell
ssh -i collaborator_key -N -L 8001:127.0.0.1:8000 collaborator@20.244.17.209
```

then browse to `http://127.0.0.1:8001`.

## Switching the webhook between the laptop and VM1

```powershell
python scripts\switch_webhook.py status        # where do GitHub's webhooks go right now?
python scripts\switch_webhook.py --to vm1      # deliver to VM1 (laptop can be switched off)
python scripts\switch_webhook.py --to laptop   # back to the smee relay and the laptop
```

It changes only the URL; the secret is the same on both receivers. Run `scripts\live_demo.ps1` on the laptop before switching back.
Only one receiver gets events at a time, so a PR is never reviewed twice.

## What was tested (17 October 2026)

| Test | Result |
|---|---|
| Service starts as `agentheal`, Gemini connected, anomaly model trained, webhook router mounted | yes |
| The VM signs in as the GitHub App with the installed credentials and sees only the one repository | yes |
| Signed `pull_request` event sent through the **public port 80** (nginx): bad signature → 401, good signature → accepted | yes |
| Full PR review run on VM1 (static tools, Gemini, summary comment, 22 inline comments, failing quality gate) | **35 s** |
| `scripts/demo_e2e.py` through a tunnel: scanner, webhook checks, five fault scenarios with live Gemini, forced false alarm | **16 / 16** |
| Auto-fix triggered with a signed `@review-bot /fix` event: repaired file + generated tests, new PR into the PR's branch | **101 s**, 9 generated tests passed |
| Unit tests on VM1 | 61 pass |

The review and fix tests were driven by signed synthetic events, so the GitHub App's webhook was **not** moved; the laptop stayed the live receiver throughout.

## Caveats

- VM1 belongs to another person's Azure subscription (your account has Contributor on `VM1_group`). Keep that in mind before storing more secrets there.
- Auto-fix executes model-written tests. On VM1 that runs as the unprivileged `agentheal` user inside the systemd sandbox, but it is still code execution; turn it off with `AUTOFIX_RUN_TESTS=0` in the unit if the VM ever reviews pull requests from strangers.
- HTTP only: the webhook is authenticated by signature, not encrypted in transit. Add a domain and TLS (for example with Let's Encrypt) before treating this as production.
- If the VM is restarted the service starts automatically (`systemctl enable`); the nginx site is already enabled.
